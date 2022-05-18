from datetime import datetime, timedelta
from statistics import median


def clean_doubles_in_simple_cards(cards, base_artist_name):
    cleaned_cards, names = [], [base_artist_name]
    for card in cards:
        if card['name'] not in names:
            cleaned_cards.append(card)
            names.append(card['name'])
    return cleaned_cards


def simplify_artist_cards(artist_cards):
    simple_cards = []
    for card in artist_cards:
        if 'artists' in card.keys() and card['artists']:
            artist_name, artist_domain, photo_url = get_artist_info_from_card_obj(card)
            if artist_name and artist_domain:
                simple_cards.append({'name': artist_name,
                                     'domain': artist_domain,
                                     'photo_url': photo_url,
                                     'links': _get_contact_links_from_card_obj(card)})
    return simple_cards


def _get_contact_links_from_card_obj(card):
    links = []
    if 'links' in card.keys() and card['links']:
        for link in card['links']:
            if 'url' in link.keys() and 'artist' not in link['url']:
                links.append(link)
    return links


def get_artist_info_from_card_obj(card):
    artist = card['artists'][0]
    artist_name, artist_domain, photo_url = None, None, None
    if 'name' in artist.keys() and 'domain' in artist.keys():
        artist_name, artist_domain = artist['name'], artist['domain']
    elif 'name' in artist.keys() and 'id' in artist.keys():
        artist_name, artist_domain = artist['name'], artist['id']
    if 'photo' in artist.keys() and artist['photo']:
        if 'url' in artist['photo'][0].keys():
            photo_url = artist['photo'][0]['url']

    return artist_name, artist_domain, photo_url


def pars_related_block_id_from_card_obj(card_obj):
    try:
        blocks = card_obj['catalog']['sections'][0]['blocks']
    except (KeyError, IndexError):
        blocks = []

    for block in blocks:
        if 'url' in block.keys() and 'related' in block['url'] and 'id' in block.keys():
            return block['id']


def pars_artist_card_section_id_and_next_from(card_obj):
    try:
        section_id = card_obj['catalog']['sections'][0]['id']
        next_from = card_obj['catalog']['sections'][0]['next_from']
        return section_id, next_from
    except (KeyError, IndexError):
        return None, None


def code_for_get_related_cards(related_links):
    code = 'return ['
    for link in related_links:
        if 'url' in link.keys():
            code += 'API.catalog.getAudioArtist({need_blocks: 1, url: "' + link['url'] + '"}), '
    code = code[:-2]
    code += '];'
    return code


def filter_artist_cards(artist_cards, listens_min=25000, listens_max=150000, n_releases=5,
                        last_days=60, median_days=60, genres=None):
    filtered_cards = []
    if not artist_cards:
        return filtered_cards

    for card in artist_cards:
        if isinstance(card, dict) and 'playlists' in card.keys() and card['playlists']:
            y = n_releases if len(card['playlists']) > n_releases else None
            releases = card['playlists'][:y]
            check = _filter_artist_by_listens(releases, listens_min, listens_max)
            if check:
                check = _filter_artist_by_last_days(releases, last_days)
            if check:
                check = _filter_artist_by_median_days(releases, median_days)
            if check:
                check = _filter_artist_by_genres(releases, genres) if genres else check
            if check:
                filtered_cards.append(card)

    return filtered_cards


def _filter_artist_by_genres(releases, genres):
    releases_genres = get_genres_from_releases(releases)
    if releases_genres:
        for genre in releases_genres:
            if genre in genres:
                return True


def get_genres_from_releases(releases):
    releases_genres = []
    for release in releases:
        if 'genre' in release.keys() and release['genres']:
            release_genres = [x['name'] for x in release['genres']]
            releases_genres.extend(release_genres)
    return releases_genres


def _filter_artist_by_listens(releases, listens_min, listens_max):
    median_listens = median([x['plays'] for x in releases])
    if listens_max >= median_listens >= listens_min:
        return True


def _filter_artist_by_last_days(releases, n_last_days):
    last_date = datetime.fromtimestamp(releases[0]['create_time'])
    today = datetime.now()
    delta = today - last_date
    if delta <= timedelta(days=n_last_days):
        return True


def _filter_artist_by_median_days(releases, median_days):
    if len(releases) == 1:
        return True

    deltas_timestamp = []
    for i in range(len(releases) - 1):
        date_1 = releases[i]['create_time']
        date_2 = releases[i + 1]['create_time']
        deltas_timestamp.append(date_1 - date_2)

    median_delta_timestamp = median(deltas_timestamp)
    median_delta = timedelta(seconds=median_delta_timestamp)
    if median_delta <= timedelta(days=median_days):
        return True
