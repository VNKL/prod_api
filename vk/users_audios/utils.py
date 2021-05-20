from collections import Counter


def code_for_get_user_audios(user_ids, n_last):
    code = 'return ['
    for user_id in user_ids:
        code += 'API.audio.get({user_id: ' + str(user_id) + ', ' \
                               'count: ' + str(n_last) + ', ' \
                               'need_user: 0, offset: 0}), '
    code = code[:-2]
    code += '];'
    return code


def unpack_resp(resp):
    if not isinstance(resp, list):
        return []

    audios = []
    for user_audios in resp:
        if user_audios and user_audios['count']:
            simple_audios = [{'artist': x['artist'], 'title': x['title']} for x in user_audios['items']]
            audios.append(simple_audios)
    return audios


def audios_to_tracks(audios):
    tracks = []
    for user_audios in audios:
        user_tracks = [f"{x['artist']} - {x['title']}" for x in user_audios]
        tracks.append(user_tracks)
    return tracks


def audios_to_artists(audios):
    artists = []
    for user_audios in audios:
        user_artists = [x['artist'] for x in user_audios]
        artists.append(user_artists)
    return artists


def calculate_counts(user_items):
    counts, users_count = [], len(user_items)

    all_items = []
    for user in user_items:
        all_items.extend(user)

    unique_items = list(set(all_items))
    counter = Counter(all_items)
    all_items_count = len(all_items)

    for item in unique_items:
        in_users_items = [1 if item in x else 0 for x in user_items]
        item_count = sum(in_users_items)
        share_users = round(item_count / users_count, 2)
        share_items = round(counter[item] / all_items_count, 2)
        counts.append({'item': item, 'share_users': share_users, 'share_items': share_items})

    counts.sort(key=lambda x: x['share_users'], reverse=True)
    return counts
