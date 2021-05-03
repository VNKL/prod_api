from datetime import datetime, timedelta
from statistics import median, mean

from api.charts.utils import search
from api.settings import CHARTS


def find_block_id(card, block_name):
    try:
        for block in card['catalog']['sections'][0]['blocks']:
            if 'url' in block.keys() and block_name in block['url']:
                return block['id']
    except (KeyError, IndexError):
        pass


def code_for_get_artist_cards_from_urls(urls_list):
    if len(urls_list) > 25:
        urls_list = urls_list[:25]

    code = 'return ['
    for url in urls_list:
        code += 'API.catalog.getAudioArtist({url: "' + url + '", need_blocks: 1}), '
    code = code[:-2]
    code += '];'

    return code


def pars_artist_from_card(card):
    if 'artists' in card.keys():
        return card['artists'][0]['name'], card['artists'][0]['id']


def pars_playlists_from_card(card):
    if 'playlists' in card.keys():
        singles, albums = [], []
        for release in card['playlists']:
            if release['count'] <= 5:
                singles.append(release)
            elif release['count'] > 5:
                albums.append(release)
        return singles, albums


def calculate_release_freq(singles, albums):
    return _calculate_release_freq(singles), _calculate_release_freq(albums)


def _calculate_release_freq(release_list):
    intervals = []
    newer_release_date = 0
    for release in release_list:
        if newer_release_date:
            intervals.append(newer_release_date - release['create_time'])
            newer_release_date = release['create_time']
        else:
            newer_release_date = release['create_time']

    if intervals:
        return timedelta(seconds=mean(intervals)).days


def pars_top_streams_tracks(card, n_top=3, simplyfy=False):
    func = lambda x: x
    if simplyfy:
        func = simplify_audio_obj
    if 'audios' in card.keys():
        if len(card['audios']) < n_top:
            return [func(x) for x in card['audios']]
        else:
            return [func(x) for x in card['audios'][:n_top]]


def simplify_audio_obj(audio):
    return {
        'name': name_from_item(audio),
        'date': datetime.fromtimestamp(audio['date'])
    }


def calculate_after_last_top(card, n_top=3):
    if 'audios' in card.keys() and 'playlists' in card.keys():
        last_top_date = _pars_last_top_date(card, n_top=n_top)
        after_top_releases = [x for x in card['playlists'] if x['create_time'] > last_top_date]
        last_release_date = card['playlists'][0]['create_time']
        return datetime.fromtimestamp(last_top_date), len(after_top_releases), datetime.fromtimestamp(last_release_date)


def _pars_last_top_date(card, n_top=3):
    top_tracks = pars_top_streams_tracks(card, n_top=n_top)
    dates = [x['date'] for x in top_tracks]
    return max(dates)


def pars_genres(card, n_last=None, n_top=None):

    top_ids = []
    if n_top:
        top_tracks = pars_top_streams_tracks(card, n_top=n_top)
        top_ids = [f"{x['album']['owner_id']}_{x['album']['id']}" for x in top_tracks]

    if 'playlists' in card.keys():
        genres = []
        releases = card['playlists']
        if n_last:
            releases = releases[:n_last] if len(releases) > n_last else releases

        for release in releases:
            if n_top and f"{release['owner_id']}_{release['id']}" in top_ids or not n_top:
                if 'genres' in release.keys():
                    genres.extend([x['name'] for x in release['genres']])

        return list(set(genres))


def get_videos_block_id(card):
    try:
        for block in card['catalog']['sections'][0]['blocks']:
            if 'url' in block.keys() and 'videos' in block['url']:
                return block['id']
    except (KeyError, IndexError):
        pass


def calculate_video_views(videos):
    if videos:
        views = [x['views'] for x in videos]
        return min(views), max(views), median(views), sum(views)
    return None, None, None, None


def calculate_videos_freq(videos_list):
    if videos_list:
        intervals = []
        newer_release_date = 0
        for video in videos_list:
            if newer_release_date:
                intervals.append(newer_release_date - video['date'])
                newer_release_date = video['date']
            else:
                newer_release_date = video['date']
        if intervals:
            return timedelta(seconds=mean(intervals)).days


def get_artist_links(card):
    if 'links' in card.keys():
        return [x for x in card['links'] if '/artist/' not in x['url']]


def calculate_all_tracks_count(list_of_obj_lists):
    count = 0
    for obj_list in list_of_obj_lists:
        for release in obj_list:
            if 'count' in release.keys():
                count += release['count']
    return count


def calculate_listens(playlists):
    listens = []
    for playlist in playlists:
        if 'plays' in playlist.keys():
            listens.append(playlist['plays'])
    if listens:
        return min(listens), max(listens), int(median(listens)), sum(listens)
    return None, None, None, None


def calculate_follows(playlists):
    followers = []
    for playlist in playlists:
        if 'followers' in playlist.keys():
            followers.append(playlist['followers'])
    if followers:
        return min(followers), max(followers), int(median(followers)), sum(followers)
    return None, None, None, None


def calculate_top_listens_and_followers(playlists, n_top):
    list_by_listen = [[x['plays'], x] for x in playlists]
    list_by_follow = [[x['followers'], x] for x in playlists]

    list_by_listen.sort(reverse=True, key=lambda x: x[0])
    list_by_follow.sort(reverse=True, key=lambda x: x[0])

    if len(list_by_listen) > n_top:
        list_by_listen = list_by_listen[:n_top]
    if len(list_by_follow) > n_top:
        list_by_follow = list_by_follow[:n_top]

    top_by_listens = [simplify_playlist_obj(x[1]) for x in list_by_listen]
    top_by_follows = [simplify_playlist_obj(x[1]) for x in list_by_follow]

    return top_by_listens, top_by_follows


def simplify_playlist_obj(playlist):
    return {
        'name': name_from_item(playlist),
        'listens': playlist['plays'],
        'followers': playlist['followers'],
        'date': datetime.fromtimestamp(playlist['create_time'])
    }


def name_from_item(item):
    if not item or 'main_artists' not in item.keys():
        return None

    name = ''

    for artist in item['main_artists']:
        name += f"{artist['name']}, "
    name = name[:-2]

    if 'featured_artists' in item.keys():
        name += ' feat. '
        for artist in item['featured_artists']:
            name += f'{artist["name"]}, '
        name = name[:-2]

    name += f" - {item['title']}"

    if 'subtitle' in item.keys():
        name += f" ({item['subtitle']})"

    return name


def simplify_link_obj(link_obj):
    link = link_obj.copy()
    for key in ['id', 'image', 'meta']:
        link.pop(key, None)
    return link


def process_audios_with_savers(audios, n_top):
    all_savers_count = 0
    tracks_savers_dict = {}
    for audio in audios:
        if 'savers_count' in audio.keys():
            savers_count = audio['savers_count']
            all_savers_count += savers_count
            track_name = f"{audio['artist']} - {audio['title']}"
            if track_name not in tracks_savers_dict.keys():
                tracks_savers_dict[track_name] = savers_count
            else:
                tracks_savers_dict[track_name] += savers_count

    if tracks_savers_dict:
        tracks_savers_list = [[v, k] for k, v in tracks_savers_dict.items()]
        tracks_savers_list.sort(reverse=True, key=lambda x: x[0])
        if len(tracks_savers_list) > n_top:
            tracks_savers_list = tracks_savers_list[:n_top]
        return [{'name': x[1], 'savers_count': x[0]} for x in tracks_savers_list], all_savers_count
    else:
        return None, None


def search_chart_releases(artist, date_from=None):
    tracks = search(artist=artist, date_from=date_from, extended=1)
    if tracks:
        processed_tracks, pos_medians = [], {}
        for track in tracks:
            processed_tracks.append(_process_chart_track_from_db(track))
            if not date_from:
                _process_pos_median(track, pos_medians)

        if date_from:
            return processed_tracks
        else:
            pos_medians = {service: round(median(pos_list)) for service, pos_list in pos_medians.items()}
            pos_medians = dict(sorted(pos_medians.items(), key=lambda item: item[1]))
            return processed_tracks, pos_medians


def _process_pos_median(track, pos_medians):
    for position in track['positions']:
        if position['service'] not in pos_medians.keys():
            pos_medians[position['service']] = [position['current']]
        else:
            pos_medians[position['service']].append(position['current'])


def _process_chart_track_from_db(track):
    processed_track = {
        'artist': track['artist'],
        'title': track['title'],
        'cover_url': track['cover_url'],
        'distributor': track['distributor']
    }
    services_dict = {}
    for position in track['positions']:
        if position['service'] not in services_dict.keys():
            services_dict[position['service']] = {'top_position': position['current'],
                                                  'last_top_date': position['date'],
                                                  'days_in_chart': 1}
        else:
            services_dict[position['service']]['days_in_chart'] += 1
            if position['current'] < services_dict[position['service']]['top_position']:
                services_dict[position['service']]['top_position'] = position['current']
                services_dict[position['service']]['last_top_date'] = position['date']
            elif position['current'] == services_dict[position['service']]['top_position']:
                if position['date'] > services_dict[position['service']]['last_top_date']:
                    services_dict[position['service']]['last_top_date'] = position['date']

    processed_track['charts'] = services_dict
    return processed_track


def calculate_tops_of_artist_by_chart(all_time_chart_tracks, n_top):
    if all_time_chart_tracks:
        charts = {x: [] for x in CHARTS}
        for track in all_time_chart_tracks:
            for service, pos_info in track['charts'].items():
                track = track.copy()
                track.pop('charts', None)
                track.update(pos_info)
                charts[service].append(track)

        top_by_days = {k: sorted(v, key=lambda x: x['days_in_chart'], reverse=True) for k, v in charts.items() if v}
        top_by_pos = {k: sorted(v, key=lambda x: x['top_position']) for k, v in charts.items() if v}

        top_by_days = {k: v[:n_top] if len(v) > n_top else v for k, v in top_by_days.items()}
        top_by_pos = {k: v[:n_top] if len(v) > n_top else v for k, v in top_by_pos.items()}

        days_median_dict = {}
        for service, tracks in charts.items():
            if tracks:
                days_median_list = [x['days_in_chart'] for x in tracks]
                days_median_dict[service] = round(median(days_median_list))
        days_median_dict = dict(sorted(days_median_dict.items(), key=lambda item: item[1], reverse=True))

        return top_by_days, top_by_pos, days_median_dict

    else:
        return None, None
