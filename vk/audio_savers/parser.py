""" Use Python 3.7 """

from datetime import date, timedelta
from multiprocessing import Process, Manager
from time import sleep
from random import uniform

from api.settings import NEW_RELEASES_SECTION_ID, CHART_BLOCK_ID, VK_PLAYLISTS, CORE_AUDIO_OWNERS
from vk.audio_savers import utils
from vk.wall_grabbing.parser import WallParser
from vk.engine import VkEngine
from vk.audio_savers_new.parser import AudioSaversNew
from vk.audio_savers_new.utils import convert_users_domains_to_execute_batches, code_for_get_users, \
    unpack_execute_get_users, slice_audios_to_id_offset_pairs, calculate_n_threads_new, slice_to_batches, \
    result_list_to_dict


def get_audio_savers_multiprocess(audios):
    vk = AudioSaversNew()
    audios_with_savers_list = []
    audios = clean_up_garbage_audios(audios)
    for n, audio in enumerate(audios):
        print(f"{n + 1} / {len(audios)}   |   {audio['artist']} - {audio['title']}   |   Start parsing audio savers ({audio['savers_count']})")
        audio_id = f"{audio['owner_id']}_{audio['audio_id']}"
        savers_list = vk.get_savers_list(audio_id=audio_id)
        audio_with_savers = utils.zip_audio_obj_and_savers(audio=audio, savers=savers_list)
        audios_with_savers_list.append(audio_with_savers)
        print(f"{n + 1} / {len(audios)}   |   {audio['artist']} - {audio['title']}   |   Finished parsing audio savers")

    return audios_with_savers_list


def clean_up_garbage_audios(audios):
    audios = [x for x in audios if x['savers_count'] > 0]
    audios_dict = {}
    for audio in audios:
        full_name = f"{audio['artist']} - {audio['title']}"
        if 'subtitle' in audio.keys():
            full_name += f" ({audio['subtitle']})"
        if full_name in audios_dict.keys():
            audios_dict[full_name].append(audio)
        else:
            audios_dict[full_name] = [audio]

    cleaned_audios = []
    for one_name_audios in audios_dict.values():
        one_name_audios.sort(key=lambda x: x['savers_count'], reverse=True)
        audio = one_name_audios[0]
        if audio['source'] == 'Поиск по аудиозаписям' and str(audio['owner_id'])[:4] in CORE_AUDIO_OWNERS:
            cleaned_audios.append(audio)
        else:
            cleaned_audios.extend(one_name_audios)

    cleaned_audios.sort(key=lambda x: x['savers_count'], reverse=True)

    return cleaned_audios


def get_audio_savers_multiprocess_new(audios):
    audios = clean_up_garbage_audios(audios=audios)
    pairs, audio_ids = slice_audios_to_id_offset_pairs(audios=audios)
    n_threads = calculate_n_threads_new(pairs=pairs)
    pairs_batches = slice_to_batches(array=pairs, n_threads=n_threads)

    result_list = Manager().list()
    finished_list = Manager().list()
    for x in range(n_threads):
        finished_list.append(0)

    processes = []
    for n in range(n_threads):
        process = Process(target=get_savers_list_one_process_new,
                          args=(pairs_batches[n], result_list, finished_list, n))
        process.start()
        processes.append(process)
        sleep(uniform(1, 2))

    parsing_in_process = True
    while parsing_in_process:
        if all(finished_list):
            parsing_in_process = False
        for n, status in enumerate(finished_list):
            if status:
                processes[n].kill()
        sleep(uniform(0.5, 1))

    for process in processes:
        process.kill()

    result_dict = result_list_to_dict(result_list=list(result_list))
    audios_with_savers_list = []
    for audio in audios:
        audio_id = f"{audio['owner_id']}_{audio['audio_id']}"
        if audio_id in result_dict.keys():
            audio_with_savers = utils.zip_audio_obj_and_savers(audio=audio, savers=result_dict[audio_id])
            audios_with_savers_list.append(audio_with_savers)

    return audios_with_savers_list


def get_savers_list_one_process_new(pairs, result_list, finished_list, n_thread):
    vk = AudioSaversNew()
    audio_savers = {}
    all_domains = []
    len_pairs = len(pairs)
    for n, pair in enumerate(pairs):
        audio_id = pair['audio_id']
        savers = vk.pars_savers_one_page(audio_id=pair['audio_id'], offset=pair['offset'])
        if savers:
            if audio_id in audio_savers.keys():
                audio_savers[audio_id].extend(savers)
            else:
                audio_savers[audio_id] = savers
            all_domains.extend(savers)
            print(f'Process {n_thread + 1} \t | \t Parsed: {n + 1} / {len_pairs}')
        else:
            print(f'Process {n_thread + 1} \t | \t Parsing error: {n + 1} / {len_pairs}')
        sleep(uniform(0.3, 0.5))

    print(f'------ Process {n_thread + 1} finished parsing savers ------')
    print(f'------ Process {n_thread + 1} start converting domains to ids ------')

    domains_unique = list(set(all_domains))
    vk = AudioSaversParser()
    domains_ids = vk.get_user_ids_from_domains(domains=domains_unique)

    print(f'------ Process {n_thread + 1} finished converting domains to ids ------')

    for audio_id, domains in audio_savers.items():
        savers_ids = [domains_ids[x] for x in domains if x in domains_ids.keys()]
        print(len(domains), len(savers_ids))
        result_list.append({audio_id: savers_ids})

    finished_list[n_thread] = 1


class AudioSaversParser(VkEngine):

    def get_by_artist_url(self, artist_card_url, count_only):
        if 'https://vk.com/artist/' not in artist_card_url:
            self.errors.append({'method': 'api/parsers/get_by_artist_url', 'param': artist_card_url,
                                'error_msg': 'Invalid artist url'})
            return None

        audios, artist_name, artist_group, artist_user = [], None, None, None
        artist_id = artist_card_url.replace('https://vk.com/artist/', '')

        resp = self._api_response('catalog.getAudioArtist', {'artist_id': artist_id, 'need_blocks': 1})
        if resp and 'artists' in resp.keys():
            artist_name = resp['artists'][0]['name']
            artist_group = utils.pars_url_from_artist_card(resp, url_type='group')
            artist_user = utils.pars_url_from_artist_card(resp, url_type='user')
            audios.extend(utils.mark_audios_by_source(resp['audios'], source='Карточка артиста'))
            search_results = self._search_audios_execute(artist_name, performer_only=1)
            audios.extend(utils.match_search_results(search_results, artist_name))
        else:
            self.errors.append({'method': 'api/parsers/get_by_artist_url', 'param': artist_card_url,
                                'error_msg': 'Artist is not found'})

        if artist_group and artist_name and count_only:
            group_audios, group_id = self.get_by_group(artist_group, count_only, earlier_return=True)
            group_wall_audios = self.get_posts_from_wall(owner_id=int(f'-{group_id}'))
            group_audios = utils.mark_audios_by_source(group_audios, source='Паблик артиста')
            group_wall_audios = utils.mark_audios_by_source(group_wall_audios, source='Пост на стене паблика артиста')
            audios.extend(utils.match_search_results(group_audios, artist_name))
            audios.extend(utils.match_search_results(group_wall_audios, artist_name))

        if artist_user and count_only:
            user_audios, user_id = self.get_by_user(artist_user, count_only, earlier_return=True)
            user_wall_audios = self.get_posts_from_wall(owner_id=user_id)
            user_audios = utils.mark_audios_by_source(user_audios, source='Личная страница артиста')
            user_wall_audios = utils.mark_audios_by_source(user_wall_audios, source='Пост на личной странице артиста')
            audios.extend(utils.match_search_results(user_audios, artist_name))
            audios.extend(utils.match_search_results(user_wall_audios, artist_name))

        if audios:
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_artist_url', 'param': artist_card_url,
                                'error_msg': 'Artist audios are not found'})

    def get_by_track_name(self, track_name, count_only):
        audios = []

        search_results = self._search_audios_execute(track_name, performer_only=0)
        audios.extend(utils.match_search_results(search_results, track_name))

        # if count_only:
        artist_ids = utils.get_artists_domains_from_audios_list(audios)
        release_upload_date = utils.get_release_upload_date(audios)
        if artist_ids:
            for artist_id in artist_ids:
                resp = self._api_response('catalog.getAudioArtist', {'artist_id': artist_id, 'need_blocks': 1})
                if resp and 'audios' in resp.keys():
                    audios.extend(utils.mark_audios_by_source(resp['audios'], source='Карточка артиста'))
                    card_pl_audios = self._search_track_in_artist_playlists(artist_card=resp, track_name=track_name)
                    audios.extend(utils.mark_audios_by_source(card_pl_audios, source='Карточка артиста'))
                    artist_group = utils.pars_url_from_artist_card(resp, url_type='group')
                    group_audios, group_id = self.get_by_group(artist_group, count_only, earlier_return=True)
                    if group_audios:
                        group_audios = utils.mark_audios_by_source(group_audios, source='Паблик артиста')
                        audios.extend(group_audios)
                    if group_id:
                        group_wall_audios = self.get_posts_from_wall(owner_id=int(f'-{group_id}'))
                        group_wall_audios = utils.mark_audios_by_source(group_wall_audios,
                                                                        source='Пост на стене паблика артиста')
                        audios.extend(group_wall_audios)
                        wall = WallParser()
                        date_from = date.fromtimestamp(release_upload_date) if release_upload_date else None
                        date_to = date_from + timedelta(days=30) if date_from else None
                        ad_posts = wall.get_group_posts(group=group_id, date_from=date_from, date_to=date_to,
                                                        with_audio=True, dark_posts_only=True, pars_playlists=True,
                                                        pars_audio_savers=False)
                        if ad_posts:
                            ad_audios = utils.iter_get_audios_from_posts(ad_posts)
                            ad_audios = utils.mark_audios_by_source(ad_audios, source='Рекламный пост')
                            audios.extend(ad_audios)

        if audios:
            audios = utils.match_search_results(audios, track_name)
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_track_name', 'param': track_name,
                                'error_msg': 'Audios are not found'})

    def get_by_group(self, group, count_only, earlier_return=False):
        audios = []

        group_id = self._get_group_id(group)
        if group_id:
            group_params = {'owner_id': f'-{group_id}'}
            audios.extend(self._offsets_get_audios_from_list(group_params))
        else:
            self.errors.append({'method': 'api/parsers/get_by_group', 'param': group,
                                'error_msg': 'Group is not found or closed'})

        if earlier_return:
            return audios, group_id

        if audios:
            audios = utils.mark_audios_by_source(audios, source='Паблик')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_group', 'param': group,
                                'error_msg': 'Audios are not found'})

    def get_by_user(self, user, count_only, earlier_return=False):
        audios = []

        user_id = self._get_user_id(user)
        if user_id:
            user_params = {'owner_id': user_id}
            audios.extend(self._offsets_get_audios_from_list(user_params))
        else:
            self.errors.append({'method': 'api/parsers/get_by_user', 'param': user,
                                'error_msg': 'User is not found or closed'})

        if earlier_return:
            return audios, user_id

        if audios:
            audios = utils.mark_audios_by_source(audios, source='Личная страница')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_user', 'param': user,
                                'error_msg': 'Audios are not found'})

    def get_by_playlist(self, playlist_url, count_only):
        audios = []

        playlist_params = utils.pars_playlist_url(playlist_url)
        if playlist_params:
            audios.extend(self._offsets_get_audios_from_list(playlist_params))
        else:
            self.errors.append({'method': 'api/parsers/get_by_playlist', 'param': playlist_url,
                                'error_msg': 'Playlist url is incorrect'})

        if audios:
            audios = utils.mark_audios_by_source(audios, source='Плейлист')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_playlist', 'param': playlist_url,
                                'error_msg': 'Audios are not found'})

    def get_by_chart(self, count_only):
        audios = self._get_block_audios(CHART_BLOCK_ID)
        if audios:
            audios = utils.mark_audios_by_source(audios, source='Чарт ВКонтакте')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_chart', 'param': None,
                                'error_msg': 'Audios are not found'})

    def get_by_new_releases(self, count_only):
        audios = self._get_section_audios(NEW_RELEASES_SECTION_ID)
        if audios:
            audios = utils.mark_audios_by_source(audios, source='Новинки')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_new_releases', 'param': None,
                                'error_msg': 'Audios are not found'})

    def get_by_newsfeed(self, q, count_only):
        audios = None
        posts = self._get_newsfeed_posts(q)
        if posts:
            audios = utils.iter_get_audios_from_posts(posts)
            audios = utils.match_search_results(audios, q)
        else:
            self.errors.append({'method': 'api/parsers/get_by_newsfeed', 'param': q,
                                'error_msg': 'Posts with audio are not found'})
        if audios:
            audios = utils.mark_audios_by_source(audios, source='Пост из поиска по новостям')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_newsfeed', 'param': q,
                                'error_msg': 'Audios are not found'})

    def get_by_post(self, post_url, count_only):
        audios, post = None, None
        post_id = utils.pars_post_id_from_post_url(post_url)
        if post_id:
            post = self._get_post(post_id)
        else:
            self.errors.append({'method': 'api/parsers/get_by_post', 'param': post_url,
                                'error_msg': 'Post url is incorrect'})
        if post:
            audios = utils.get_audios_from_post(post)
        else:
            self.errors.append({'method': 'api/parsers/get_by_post', 'param': post_url,
                                'error_msg': 'Error with get post object'})
        if audios:
            audios = utils.mark_audios_by_source(audios, source='Пост')
            audios = utils.clean_audio_doubles(audios)
            return self.get_by_audios(audios, count_only, n_threads=8)
        else:
            self.errors.append({'method': 'api/parsers/get_by_post', 'param': post_url,
                                'error_msg': 'Audios are not found'})

    def get_by_audios(self, audio_objects, count_only, n_threads=None):
        check_dicts, audios = [None], None

        if isinstance(audio_objects, dict):
            audios = [audio_objects]
        elif isinstance(audio_objects, list):
            audios = audio_objects

        if isinstance(audio_objects, list):
            check_dicts = [True if isinstance(x, dict) else False for x in audios]

        if all(check_dicts):
            audios = utils.clean_audio_doubles(audios)
        else:
            self.errors.append({'method': 'api/parsers/get_by_audios', 'param': audio_objects,
                                'error_msg': 'Audio objects are incorrect'})

        if audios:
            audios = self._get_savers_count(audios)
            if not count_only:
                audios = utils.process_audios_by_has_core(audios)
            if count_only:
                return audios
            if n_threads:
                return get_audio_savers_multiprocess_new(audios)
            else:
                return self.iter_get_audios_savers(audios)
        else:
            self.errors.append({'method': 'api/parsers/get_by_audios', 'param': audio_objects,
                                'error_msg': 'Audios are not found after doubles cleaning'})

    def get_posts_from_wall(self, owner_id):
        posts = []
        actual_wall = self._api_response('wall.get', {'owner_id': f'{owner_id}', 'count': 100})
        if actual_wall:
            posts.extend(actual_wall['items'])

        return utils.iter_get_audios_from_posts(posts)

    def iter_get_audios_savers(self, audios):
        audios_with_savers = []
        for n, audio in enumerate(audios):
            audio_id = audio['id'] if 'id' in audio.keys() else audio['audio_id']
            audio_savers = self._get_audio_savers(audio['owner_id'], audio_id)
            if isinstance(audio_savers, list):
                audios_with_savers.append(utils.zip_audio_obj_and_savers(audio, audio_savers))
            try:
                print(f'{n+1} / {len(audios)} \t | \t {audio["artist"]} - {audio["title"]}')
            except OSError:
                pass
        return audios_with_savers

    def get_user_ids_from_domains(self, domains):
        users_ids_dict = {}
        domains_execute_batches = convert_users_domains_to_execute_batches(domains=domains)
        for batch in domains_execute_batches:
            code = code_for_get_users(batch=batch)
            execute_resp = self._execute_response(code)
            if execute_resp:
                batch_dict = unpack_execute_get_users(resp=execute_resp)
                users_ids_dict.update(batch_dict)

        return users_ids_dict

    def _search_track_in_artist_playlists(self, artist_card, track_name):
        if 'playlists' not in artist_card.keys():
            return []
        if ' - ' in track_name:
            title = track_name.split(' - ')[1]
        else:
            title = track_name

        audios = []
        for playlist in artist_card['playlists']:
            if playlist['title'] == title:
                params = {'owner_id': playlist['owner_id'],
                          'playlist_id': playlist['id'],
                          'access_key': playlist['access_key']}
                audios.extend(self._offsets_get_audios_from_list(params))

        return audios

    def _get_block_audios(self, block_id):
        audios = []
        next_from = None
        i = 0
        while True:
            resp = self._get_block_response(block_id, next_from)
            if resp:
                for n, audio in enumerate(resp['block']['audios']):
                    if block_id == CHART_BLOCK_ID:
                        chart_position = n + i * 20 + 1
                        audio['chart_position'] = chart_position
                    audios.append(audio)
                if 'next_from' in resp['block']:
                    next_from = resp['block']['next_from']
                    i += 1
                else:
                    break
            else:
                break
        return audios

    def _get_section_audios(self, section_id):
        audios = []
        next_from = None
        while True:
            resp = self._get_section_response(section_id, next_from)
            if resp:
                if 'audios' in resp.keys():
                    audios.extend(resp['audios'])
                if 'section' in resp.keys() and resp['section'] and 'next_from' in resp['section'].keys():
                    next_from = resp['section']['next_from']
                else:
                    break
            else:
                break
        return audios

    def _get_block_response(self, block_id, next_from=None):
        api_method_params = {'block_id': block_id, 'start_from': next_from, 'extended': 1}
        return self._api_response('audio.getCatalogBlockById', api_method_params)

    def _get_section_response(self, section_id, next_from=None):
        api_method_params = {'section_id': section_id, 'start_from': next_from, 'extended': 1}
        return self._api_response('catalog.getSection', api_method_params)

    def _offsets_get_audios_from_list(self, method_params_dict):
        count = 0
        audios = []
        resp = self._api_response('audio.get', method_params_dict)
        if resp and 'items' in resp.keys() and 'count' in resp.keys():
            audios.extend(resp['items'])
            count = resp['count']

        if count > 200:
            for offset in range(200, count, 200):
                params = method_params_dict.copy()
                params['offset'] = offset
                offset_resp = self._api_response('audio.get', params)
                if offset_resp:
                    audios.extend(offset_resp['items'])

        return audios

    def _get_savers_count(self, audios):
        vk = AudioSaversNew()
        audio_ids = [f"{x['owner_id']}_{x['id']}" for x in audios]
        saves_counters = vk.get_savers_count(audio_ids=audio_ids)
        audios_with_savers_count = utils.iter_zip_audio_obj_and_savers_new(audios, saves_counters)

        return audios_with_savers_count

    def _get_audio_savers(self, owner_id, audio_id):
        params = {'type': 'audio', 'owner_id': owner_id, 'item_id': audio_id, 'count': 1}
        resp = self._api_response('likes.getList', params)
        if resp and 'count' in resp.keys():
            return self._offsets_get_audio_savers(owner_id, audio_id, resp['count'])

    def _offsets_get_audio_savers(self, owner_id, audio_id, count):
        offsets_list = list(range(0, count, 1000))
        offsets_batches = []
        for x in range(0, len(offsets_list), 25):
            y = x + 25 if x + 25 <= len(offsets_list) else None
            offsets_batches.append(offsets_list[x:y])

        savers = []
        for offsets_batch in offsets_batches:
            code = utils.code_for_iter_get_audio_savers(owner_id, audio_id, offsets_batch)
            execute_resp = self._execute_response(code)
            if execute_resp:
                savers.extend(utils.unpack_execute_response_with_audio_savers(execute_resp))

        return savers

    def _search_audios(self, q, performer_only: int):
        responses = []
        for sort in [0, 2]:
            for offset in range(0, 1000, 300):
                params = {'q': q, 'performer_only': performer_only, 'count': 300, 'offset': offset, 'sort': sort}
                responses.append(self._api_response('audio.search', params))

        audios = []
        for resp in responses:
            if resp and 'items' in resp.keys():
                audios.extend(resp['items'])

        return audios

    def _search_audios_execute(self, q, performer_only: int):
        audios = []

        code = utils.code_for_search_audios(q, performer_only)
        execute_resp = self._execute_response(code)
        if execute_resp:
            for x in execute_resp:
                if 'items' in x.keys() and x['items']:
                    finded_audios = utils.mark_audios_by_source(x['items'], source='Поиск по аудиозаписям')
                    audios.extend(finded_audios)

        chart_audios = self._get_block_audios(CHART_BLOCK_ID)
        new_releases = self._get_section_audios(NEW_RELEASES_SECTION_ID)
        audios.extend(utils.mark_audios_by_source(chart_audios, source='Чарт ВКонтакте'))
        audios.extend(utils.mark_audios_by_source(new_releases, source='Новинки'))

        for playlist_url, playlist_name in VK_PLAYLISTS.items():
            playlist_params = utils.pars_playlist_url(playlist_url)
            if playlist_params:
                playlist_audios = self._offsets_get_audios_from_list(playlist_params)
                audios.extend(utils.mark_audios_by_source(playlist_audios, source=playlist_name))

        posts = self._get_newsfeed_posts(q)
        if posts:
            posts_audios = utils.iter_get_audios_from_posts(posts)
            audios.extend(utils.mark_audios_by_source(posts_audios, source='Пост из поиска по новостям'))

        if not performer_only:
            domains = utils.get_artists_domains_from_audios_list(audios)
            if domains:
                for domain in domains:
                    resp = self._api_response('catalog.getAudioArtist', {'artist_id': domain, 'need_blocks': 1})
                    if resp and 'audios' in resp.keys():
                        audios.extend(utils.mark_audios_by_source(resp['audios'], source='Карточка артиста'))

        return audios

    def _get_group_id(self, group):
        group_id = None

        if isinstance(group, int):
            group_id = group

        elif isinstance(group, str):
            if 'https://vk.com/public' in group:
                group_id = group.replace('https://vk.com/public', '')
            elif 'https://vk.com/' in group:
                group_id = group.replace('https://vk.com/', '')

        if group_id:
            resp = self._api_response('groups.getById', {'group_id': group_id})
            if resp and 'id' in resp[0].keys():
                return resp[0]['id']

    def _get_user_id(self, user):
        user_id = None

        if isinstance(user, int):
            user_id = user

        elif isinstance(user, str):
            if 'https://vk.com/' in user:
                user_id = user.replace('https://vk.com/', '')

        if user_id:
            resp = self._api_response('users.get', {'user_ids': user_id})
            if resp and 'id' in resp[0].keys():
                return resp[0]['id']

    def _get_newsfeed_posts(self, q):
        posts = []
        next_from = None
        for _ in range(4):
            resp = self._api_response('newsfeed.search', {'q': q, 'attach': 3, 'count': 200, 'start_from': next_from})
            if resp and 'items' in resp.keys():
                posts.extend(resp['items'])
            if resp and 'next_from' in resp.keys():
                next_from = resp['next_from']
        posts.reverse()
        return posts

    def _get_post(self, post_id):
        resp = self._api_response('wall.getById', {'posts': post_id})
        if resp:
            return resp[0]
