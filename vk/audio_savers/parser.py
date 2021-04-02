""" Use Python 3.7 """

from time import sleep
from datetime import date, timedelta
from multiprocessing import Process, Manager

from api.settings import NEW_RELEASES_SECTION_ID, CHART_BLOCK_ID, VK_PLAYLISTS
from vk.audio_savers import utils
from vk.wall_grabbing.parser import WallParser
from vk.engine import VkEngine


def get_audio_savers_multiprocess(audios, n_threads):

    audios_batches = _batch_audios_list(audios, n_threads)
    result_list = Manager().list()
    processes = [Process(target=_pars_audios_batch, args=(x, result_list)) for x in audios_batches]
    for p in processes:
        p.start()
        sleep(1)
    for p in processes:
        p.join()
    return result_list


def _batch_audios_list(audios, n_threads):
    batches_list = [[] for _ in range(n_threads)]
    n = 0
    for audio in audios:
        if n + 1 <= n_threads:
            batches_list[n].append(audio)
            n += 1
        else:
            batches_list[0].append(audio)
            n = 1
    return batches_list


def _pars_audios_batch(audios, result_list):
    vk = AudioSaversParser()
    savers = vk.iter_get_audios_savers(audios=audios)
    if savers:
        result_list.extend(savers)


class AudioSaversParser(VkEngine):

    def get_by_artist_url(self, artist_card_url, count_only):
        audios, artist_name, artist_group, artist_user = [], None, None, None
        artist_id = artist_card_url.replace('https://vk.com/artist/', '')

        resp = self._api_response('catalog.getAudioArtist', {'artist_id': artist_id, 'need_blocks': 1})
        if resp:
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

        if count_only:
            artist_ids = utils.get_artists_domains_from_audios_list(audios)
            release_upload_date = utils.get_release_upload_date(audios)
            if artist_ids:
                for artist_id in artist_ids:
                    resp = self._api_response('catalog.getAudioArtist', {'artist_id': artist_id, 'need_blocks': 1})
                    if resp:
                        audios.extend(utils.mark_audios_by_source(resp['audios'], source='Карточка артиста'))
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
                return get_audio_savers_multiprocess(audios, n_threads)
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
        audio_batches = []
        for x in range(0, len(audios), 25):
            y = x + 25 if x + 25 <= len(audios) else None
            audio_batches.append(audios[x:y])

        audios_with_savers_count = []
        for batch in audio_batches:
            code = utils.code_for_get_savers_count(batch)
            execute_resp = self._execute_response(code)
            if execute_resp:
                audios_with_savers_count.extend(utils.iter_zip_audio_obj_and_savers(batch, execute_resp))

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
                    if resp:
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
            resp = self._api_response('groups.getById', {'group_id': group_id, 'fields': 'counters'})
            if resp and resp[0]['counters']['audios']:
                return resp[0]['id']

    def _get_user_id(self, user):
        user_id = None

        if isinstance(user, int):
            user_id = user

        elif isinstance(user, str):
            if 'https://vk.com/' in user:
                user_id = user.replace('https://vk.com/', '')

        if user_id:
            resp = self._api_response('users.get', {'user_ids': user_id, 'fields': 'counters'})
            if resp and resp[0]['counters']['audios']:
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
        return posts

    def _get_post(self, post_id):
        resp = self._api_response('wall.getById', {'posts': post_id})
        if resp:
            return resp[0]