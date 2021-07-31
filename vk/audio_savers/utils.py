""" Use Python 3.7 """
from api.settings import CORE_AUDIO_OWNERS


def pars_playlist_url(playlist_url):
    """
    Возвращает дикст с параметрами плейлиста, распарсенными из ссылки на плейлист

    :param playlist_url:    str, полная ссылка на плейлист в ВК (из "поделиться" -> "экспортировать")
    :return:                dict, {'owner_id': str, 'playlist_id': str, 'access_key': str}
    """
    owner_id, playlist_id, access_key = None, None, None
    if isinstance(playlist_url, str):
        if 'playlist' in playlist_url:
            owner_id, playlist_id, access_key = playlist_url.replace('https://vk.com/music/playlist/', '').split('_')
        elif 'album' in playlist_url:
            owner_id, playlist_id, access_key = playlist_url.replace('https://vk.com/music/album/', '').split('_')
    if owner_id:
        return {'owner_id': owner_id, 'playlist_id': playlist_id, 'access_key': access_key}


def match_search_results(search_results, q):
    """
    Возвращает лист объектов аудиозаписей, полученных из поиска, которые сходятся с поисковым запросом

    :param search_results:      list, лист объектов аудиозаписей ВК
    :param q:                   str, поисковый запрос в формате "artist - title" или просто "q"
    :return:                    list, лист объектов аудиозаписей ВК
    """
    artist, title = q, None
    if ' - ' in q:
        artist, title = q.split(' - ') if len(q.split(' - ')) == 2 else (q.split(' - ')[0], ' - '.join(q.split(' - ')[1:]))

    searched_artists = []
    for symbol in [', ', ' feat ', ' feat. ', ' ft ', ' ft. ',  'Feat ', ' Feat. ', ' Ft ',  ' Ft. ', ' FEAT ', ' FEAT. ', ' FT ', ' FT. ']:
        if symbol in artist:
            searched_artists = artist.split(symbol)
    if not searched_artists:
        searched_artists = [artist]

    matched_audios = []
    for audio in search_results:
        artists = [x['name'].lower() for x in audio['main_artists']] if 'main_artists' in audio.keys() else []
        artists += [x['name'].lower() for x in audio['featured_artists']] if 'featured_artists' in audio.keys() else []
        check_artists = [True if x.lower() in artists else False for x in searched_artists]
        if any(check_artists) and title:
            audio_title = f"{audio['title']} ({audio['subtitle']})" if 'subtitle' in audio.keys() else audio['title']
            if title in audio_title:
                matched_audios.append(audio)
        elif any(check_artists):
            matched_audios.append(audio)

    return matched_audios


def iter_zip_audio_obj_and_savers(audios, execute_response):
    """
    Возвращает лист упрощенных объектов аудиозаписей с количеством их добавлений и,
    если переданы айди людей, которые добавили аудио, с листом айди добавивших людей

    :param audios:              list, лист объектов аудиозаписей ВК
    :param execute_response:    dict, ответ метода execute АПИ ВК
    :return:                    list, лист упрощенных и обновленных объектов аудиозаписей ВК
    """
    audios_with_savers_count = []
    for n, audio in enumerate(audios):
        savers_count = None
        if execute_response[n]:
            savers_count = execute_response[n]['count']
        zipped = zip_audio_obj_and_savers(audio, savers_count)
        audios_with_savers_count.append(zipped)
    return audios_with_savers_count


def iter_zip_audio_obj_and_savers_new(audios, savers_counters):
    """
    Возвращает лист упрощенных объектов аудиозаписей с количеством их добавлений и,
    если переданы айди людей, которые добавили аудио, с листом айди добавивших людей

    :param audios:              list, лист объектов аудиозаписей ВК
    :param savers_counters:     dict, дикт {full_audio_id: savers_count}
    :return:                    list, лист упрощенных и обновленных объектов аудиозаписей ВК
    """
    audios_with_savers_count = []
    for audio in audios:
        audio_id = f"{audio['owner_id']}_{audio['id']}"
        savers_count = savers_counters[audio_id] if audio_id in savers_counters.keys() else None
        zipped = zip_audio_obj_and_savers(audio, savers_count)
        audios_with_savers_count.append(zipped)
    return audios_with_savers_count


def zip_audio_obj_and_savers(audio, savers):

    audio_obj = {
        'owner_id': audio['owner_id'],
        'audio_id': audio['id'] if 'id' in audio.keys() else audio['audio_id'],
        'artist': audio['artist'],
        'title': f"{audio['title']} ({audio['subtitle']})" if 'subtitle' in audio.keys() else audio['title'],
        'date': audio['date'],
        'source': audio['source'] if 'source' in audio.keys() else None,
        'doubles': audio['doubles'] if 'doubles' in audio.keys() else None,
        'savers_count': 0
    }
    if 'chart_position' in audio.keys():
        audio_obj.update({'chart_position': audio['chart_position']})
    if 'post_owner_id' in audio.keys():
        audio_obj.update({'post_owner_id': audio['post_owner_id'], 'post_id': audio['post_id']})
    if isinstance(savers, list):
        audio_obj.update({'savers': savers, 'savers_count': len(savers)})
    elif isinstance(savers, int):
        audio_obj.update({'savers_count': savers})
    return audio_obj


def clean_audio_doubles(audios):
    """
    Возвращает лист объектов аудиозаписей ВК, очищенный от повторений

    :param audios:      list, лист объектов аудиозаписей ВК
    :return:            list, лист объектов аудиозаписей ВК
    """
    try:
        cleaned_audios = {}
        for audio in audios:
            audio = audio.copy()
            audio['doubles'] = 0
            audio_id = audio['id'] if 'id' in audio.keys() else audio['audio_id']
            audio_str = f'{audio["owner_id"]}_{audio_id}'
            if audio_str not in cleaned_audios.keys():
                cleaned_audios[audio_str] = audio
            else:
                n_doubles = cleaned_audios[audio_str]['doubles'] if 'doubles' in cleaned_audios[audio_str].keys() else 0
                n_doubles += 1
                audio = replace_doubles_decision(audio_1=cleaned_audios[audio_str], audio_2=audio)
                audio['doubles'] = n_doubles
                cleaned_audios[audio_str] = audio

        return list(cleaned_audios.values())

    except (KeyError, IndexError, Exception):
        return None


def replace_doubles_decision(audio_1, audio_2):
    priority = {
        'Карточка артиста': 1,
        'Паблик артиста': 10,
        'Пост на стене паблика артиста': 6,
        'Личная страница артиста': 11,
        'Пост на личной странице артиста': 7,
        'Рекламный пост': 8,
        'Паблик': 13,
        'Личная страница': 14,
        'Плейлист': 5,
        'Лучшее за неделю': 5,
        'Сегодня в плеере': 5,
        'Русские хиты': 5,
        'Русский хип-хоп': 5,
        'Танцевальная музыка': 5,
        'Зарубежный поп': 5,
        'Иностранный хип-хоп': 5,
        'Поющие блогеры': 5,
        'Иностранный рок': 5,
        'Где-то слышал': 5,
        'Новый русский рок': 5,
        'Находки недели': 5,
        'Чарт ВКонтакте': 6,
        'Новинки': 2,
        'Пост из поиска по новостям': 12,
        'Пост': 9,
        'Поиск по аудиозаписям': 3
    }

    audio_1_priority = priority[audio_1['source']]
    audio_2_priority = priority[audio_2['source']]

    if not audio_1_priority and not audio_2_priority:
        return audio_1
    elif audio_1_priority and not audio_2_priority:
        return audio_1
    elif not audio_1_priority and audio_2_priority:
        return audio_2
    elif audio_1_priority < audio_2_priority:
        return audio_1
    elif audio_1_priority > audio_2_priority:
        return audio_2
    elif audio_1_priority == audio_2_priority and audio_1_priority == 12:
        audio_1_post_owner = audio_1['post_owner'] if 'post_owner' in audio_1.keys() else None
        audio_2_post_owner = audio_2['post_owner'] if 'post_owner' in audio_2.keys() else None
        if not audio_2_post_owner and not audio_2_post_owner:
            return audio_1
        elif audio_1_post_owner < audio_2_post_owner:
            return audio_1
        elif audio_1_post_owner > audio_2_post_owner:
            return audio_2
        else:
            return audio_1

    else:
        return audio_1


def process_audios_by_has_core(audios):
    audios_dict = {}
    for audio in audios:
        name = f"{audio['artist']} - {audio['title']}"
        if 'subtitle' in audio.keys():
            name += f" ({audio['subtitle']})"

        if name not in audios_dict.keys():
            audios_dict[name] = [audio]
        else:
            audios_dict[name].append(audio)

    processed_audios = []
    for audios_list in audios_dict.values():
        sorted_list = sorted(audios_list, key=lambda x: x['savers_count'], reverse=True)
        max_savers_audio = sorted_list[0]
        if str(max_savers_audio['owner_id'])[:4] in CORE_AUDIO_OWNERS:
            processed_audios.append(sorted_list[0])
        else:
            processed_audios.extend(sorted_list)

    return processed_audios


def code_for_iter_get_audio_savers(owner_id, audio_id, offsets_batch):
    """
    Возвращает параметр code для метода execute АПИ ВК для итерирования по аудиозаписям
    для получения айди людей, эти аудиозаписи добавивших

    :param owner_id:        int, owner_id объекта аудиозаписи ВК
    :param audio_id:        int, audio_id объекта аудиозаписи ВК
    :param offsets_batch:   list, лист с параметрами offset
    :return:                str
    """
    code = 'return ['
    for offset in offsets_batch:
        tmp = 'API.likes.getList({type: "audio", count: 1000, ' \
                                 'owner_id: ' + str(owner_id) + ', ' \
                                 'item_id: ' + str(audio_id) + ', ' \
                                 'offset: ' + str(offset) + '}), '
        code += tmp
    code = code[:-2]
    code += '];'
    return code


def code_for_get_savers_count(audios_batch):
    """
    Возвращает параметр code для метода execute АПИ ВК для итерирования по аудиозаписям
    для получения количества людей, эти аудиозаписи добавивших

    :param audios_batch:    list, лист с объектами аудиозаписей
    :return:                str
    """
    code = 'return ['
    for audio in audios_batch:
        audio_id = audio['id'] if 'id' in audio.keys() else audio['audio_id']
        tmp = 'API.likes.getList({type: "audio", count: 1000, ' \
                                 'owner_id: ' + str(audio["owner_id"]) + ', ' \
                                 'item_id: ' + str(audio_id) + ', count: 1}), '
        code += tmp
    code = code[:-2]
    code += '];'
    return code


def code_for_search_audios(q, performer_only):
    code = 'return ['
    for sort in [0, 2]:
        # for offset in range(0, 1000, 300):
        code += 'API.audio.search({q: "' + q + '", performer_only: ' + str(performer_only) + ', ' \
                                  'count: 300, offset: ' + str(0) + ', sort: ' + str(sort) + '}), '
    code = code[:-2]
    code += '];'
    return code


def get_artists_domains_from_audios_list(audios):
    if not audios:
        return None

    domains = []
    for audio in audios:
        if 'is_licensed' in audio.keys() and audio['is_licensed']:
            if 'main_artists' in audio.keys():
                for artist in audio['main_artists']:
                    if 'domain' in artist.keys():
                        domains.append(artist['domain'])
            if 'featured_artists' in audio.keys():
                for artist in audio['featured_artists']:
                    if 'domain' in artist.keys():
                        domains.append(artist['domain'])
            break
    return list(set(domains))


def get_release_upload_date(audios):
    if not audios:
        return None

    for audio in audios:
        if 'is_licensed' in audio.keys() and audio['is_licensed']:
            return audio['date']


def unpack_execute_response_with_audio_savers(execute_response):
    """
    Возвращает распакованный ответ метода execute АПИ ВК с айди людей

    :param execute_response:    list, ответ метода execute АПИ ВК
    :return:                    list, лист с айди людей
    """
    savers = []
    for x in execute_response:
        if x:
            savers.extend(x['items'])
    return savers


def iter_get_audios_from_posts(posts):
    audios = []
    for post in posts:
        audios.extend(get_audios_from_post(post))
    return audios


def get_audios_from_post(post):
    if 'attachments' in post.keys():
        audios = [x['audio'] for x in post['attachments'] if x['type'] == 'audio']
        for audio in audios:
            audio.update({'post_owner_id': post['owner_id'], 'post_id': post['id']})
        return audios
    return []


def pars_post_id_from_post_url(post_url):
    if 'wall' not in post_url:
        if '_' in post_url:
            owner_id, post_id = post_url.split('-')
            try:
                owner_id, post_url = int(owner_id), int(post_id)
                return f'{owner_id}_{post_id}'
            except TypeError:
                return None
    else:
        return post_url.split('wall')[-1]


def pars_url_from_artist_card(artist_card, url_type):
    if 'links' in artist_card.keys():
        for link in artist_card['links']:
            if 'meta' in link.keys():
                if 'content_type' in link['meta'].keys() and link['meta']['content_type'] == url_type:
                    return link['url']


def mark_audios_by_source(audios, source):
    if not audios:
        return []

    marked_audios = []
    for audio in audios:
        audio = audio.copy()
        audio['source'] = source
        marked_audios.append(audio)

    return marked_audios
