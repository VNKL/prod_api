def check_date_in_period(post_date, date_from, date_to):
    if date_to and post_date <= date_to:
        if date_from and post_date >= date_from:
            return True
        elif not date_from:
            return True
    elif not date_to and date_from and post_date >= date_from:
        return True
    elif not date_from and not date_to:
        return True


def code_for_get_wall(owner_id, offset):
    code = 'return ['
    for offset in range(offset, offset + 1000, 100):
        code += 'API.wall.get({owner_id: ' + str(owner_id) + ', count: 100, offset: ' + str(offset) + '}), '
    code = code[:-2]
    code += '];'
    return code


def code_for_get_by_id(owner_id, ids_batches):
    code = 'return ['
    for batch in ids_batches:
        ids_str = ''
        for post_id in batch:
            ids_str += f'{owner_id}_{post_id},'
        code += 'API.wall.getById({posts: "' + str(ids_str) + '"}), '
    code = code[:-2]
    code += '];'
    return code


def code_for_get_posts_audio_savers_count(posts):
    code = 'return ['
    for post in posts:
        audio = [x['audio'] for x in post['attachments'] if x['type'] == 'audio'][0]
        code += 'API.likes.getList({type: "audio", count: 1, ' \
                                   'owner_id: ' + str(audio['owner_id']) + ', ' \
                                   'item_id: ' + str(audio['id']) + '}).count, '
    code = code[:-2]
    code += '];'
    return code


def code_for_get_post_audios_savers_count(post):
    code = 'return ['
    for attach in post['attachments']:
        if attach['type'] == 'audio':
            audio = attach['audio']
            code += 'API.likes.getList({type: "audio", count: 1, ' \
                                       'owner_id: ' + str(audio['owner_id']) + ', ' \
                                       'item_id: ' + str(audio['id']) + '}).count, '
    code = code[:-2]
    code += '];'
    return code


def filter_posts_for_audio_savers(posts):
    with_one_audio, with_many_audios, without_audio = [], [], []
    for post in posts:
        if 'attachments' in post.keys():
            has_audio_checks = [True if x['type'] == 'audio' else False for x in post['attachments']]
            audios_count = len([1 for x in post['attachments'] if x['type'] == 'audio'])
            if any(has_audio_checks) and audios_count == 1:
                with_one_audio.append(post)
            elif any(has_audio_checks) and audios_count > 1:
                with_many_audios.append(post)
            else:
                without_audio.append(post)
        else:
            without_audio.append(post)
    return with_many_audios, with_one_audio, without_audio


def filter_post_by_has_playlist(posts):
    with_playlist, without_playlist = [], []
    for post in posts:
        if 'attachments' in post.keys():
            has_playlist_checks = [True if x['type'] == 'playlist' else False for x in post['attachments']]
            if any(has_playlist_checks):
                with_playlist.append(post)
            else:
                without_playlist.append(post)
        else:
            without_playlist.append(post)

    return with_playlist, without_playlist


def code_for_get_playlists_listens(posts):
    code = 'return ['
    for post in posts:
        playlist = [x['playlist'] for x in post['attachments'] if x['type'] == 'playlist'][0]
        code += 'API.audio.getPlaylistById({owner_id: ' + str(playlist['owner_id']) + ', ' \
                                           'playlist_id: ' + str(playlist['id']) + ', ' \
                                           'access_key: "' + str(playlist['access_hash']) +'"}), '
    code = code[:-2]
    code += '];'
    return code


def pars_playlist_params_from_url(playlist_url):
    access_hash = None
    step_1 = playlist_url.split('playlist')[1]
    step_2 = step_1.split('&')
    pl_owner, pl_id = step_2[0].split('_')
    if 'access_hash' in step_2[1]:
        access_hash = step_2[1].split('=')[1]
    return pl_owner, pl_id, access_hash
