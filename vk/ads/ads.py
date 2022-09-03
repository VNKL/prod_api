import copy
import json
import requests

from time import sleep
from random import uniform
from bs4 import BeautifulSoup

from api.settings import RUCAPTCHA_KEY
from vk.engine import VkEngine, anticaptcha
from vk.ads import utils
from vk.audio_likes.parser import AudioLikes
from api.accounts.utils import release_proxy, load_proxy


API_SLEEPING_ERRORS = [1, 6, 10]        # Ошибка АПИ ВК, для которых просят тповторить запрос позже
TOKEN_FATAL_ERRORS = [4, 5, 17, 5]      # Ошибки АПИ ВК, связанные с потерей аккаунта
TOKEN_SLEEPING_ERRORS = [9, 29]         # Ошибки АПИ ВК, связанные с заморозкой токена на определенный метод


class VkAds(VkEngine):

    def __init__(self, ads_token):
        super().__init__()
        self.ads_token = ads_token
        self.ads_errors = []
        self.ads_n_try = 0
        self.playlist_cover = None

    def _get_ads_response(self, url, data, captcha_sid=None, captcha_key=None, reset_n_try=True):
        """
        Возвращает ответ апи ВК, отбиваясь от капчи и ту мэни реквестс пер секонд

        :param url:             str, урл запроса к апи с названием метода (без параметров!!!)
        :param data:            dict, дикт с параметрами метода
        :param captcha_sid:     str, сид капчи
        :param captcha_key:     str, разгаданная капча
        :return:                dict, разобранный из JSON ответ апи ВК (None - если ошибка в ответе)
        """
        sleep(uniform(0.4, 0.6))

        if reset_n_try:
            self.ads_n_try = 0

        proxy_dict = {'http': f'http://{self.proxy}'} if self.proxy else None

        if captcha_sid and captcha_key:
            if data:
                data.update({'captcha_sid': captcha_sid, 'captcha_key': captcha_key})
            else:
                data = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}

        try:
            resp = requests.post(url, data, proxies=proxy_dict).json()
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            return self._handle_ads_requests_error(url, data, captcha_sid, captcha_key)

        if 'error' in resp.keys():
            return self._handle_ads_api_error(captcha_key, captcha_sid, data, resp, url)
        else:
            return resp['response']

    def _ads_response(self, method, params=None, n_try=0):
        """
        Возвращает ответ от API ВК (None - если ошибка)

        :param method:  str, название метода API ВК
        :param params:  dict, параметры метода
        :return:        dict, разобранный из JSON ответ апи ВК (None - если ошибка)
        """
        url = f'https://api.vk.com/method/{method}'
        if params:
            params.update({'access_token': self.ads_token, 'v': 5.96})
        else:
            params = {'access_token': self.ads_token, 'v': 5.96}

        resp = self._get_ads_response(url=url, data=params)
        if not resp and n_try < 3:
            return self._ads_response(method, params, n_try=n_try + 1)
        else:
            return resp

    def _execute_ads_response(self, code):
        return self._ads_response('execute', {'code': code})

    def _handle_ads_requests_error(self, url, data, captcha_sid, captcha_key):
        if self.ads_n_try < 10:
            release_proxy(self.proxy)
            self.proxy = load_proxy()
            sleep(uniform(3, 10))
            self.ads_n_try += 1
            return self._get_ads_response(url, data, captcha_sid, captcha_key, reset_n_try=False)
        else:
            self.errors.append({'error_msg': 'VK API request max retries error'})

    def _handle_ads_api_error(self, captcha_key, captcha_sid, data, resp, url):

        if resp['error']['error_msg'] == 'Captcha needed':
            captcha_sid = resp['error']['captcha_sid']
            captcha_img = resp['error']['captcha_img']
            captcha_key = anticaptcha(captcha_img, RUCAPTCHA_KEY)
            if captcha_key:
                return self._get_ads_response(url, data, captcha_sid, captcha_key, reset_n_try=False)
            else:
                self.errors.append(resp['error'])
                return None

        elif resp['error']['error_code'] in API_SLEEPING_ERRORS:
            if self.ads_n_try < 10:
                self.ads_n_try += 1
                sleep(uniform(20, 40))
                return self._get_ads_response(url, data, captcha_sid, captcha_key, reset_n_try=False)
            else:
                self.errors.append(resp['error'])
                return None

        elif resp['error']['error_code'] in TOKEN_FATAL_ERRORS:
            self.errors.append(resp['error'])
            return None

        elif resp['error']['error_code'] in TOKEN_SLEEPING_ERRORS:
            if self.ads_n_try < 10:
                self.ads_n_try += 1
                sleep(uniform(5, 15))
                return self._get_ads_response(url, data, captcha_sid, captcha_key, reset_n_try=False)
            else:
                self.errors.append(resp['error'])
                return None

        elif resp['error']['error_code'] == 602:
            return resp['response'] if 'response' in resp.keys() else resp

        else:
            self.errors.append(resp['error'])
            return None

    def get_cabs_and_groups(self):
        cabinets, groups, cab_roles = [], [], ['admin', 'manager']
        code = utils.code_for_get_cabs_and_groups()
        resp = self._execute_ads_response(code)
        if resp and 'cabinets' in resp.keys() and 'groups' in resp.keys():
            cabinets.extend(resp['cabinets'])
            groups.extend(resp['groups']['items'])

        if cabinets:
            agency_cabs = [x for x in cabinets if x['account_type'] == 'agency' and x['access_role'] in cab_roles]
            general_cabs = [x for x in cabinets if x['account_type'] == 'general' and x['access_role'] in cab_roles]

            if agency_cabs:
                for cab in agency_cabs:
                    resp = self._ads_response('ads.getClients', {'account_id': cab['account_id']})
                    if resp:
                        for client in resp:
                            cab = cab.copy()
                            cab.update({'client_id': client['id'], 'client_name': client['name']})
                            general_cabs.append(cab)

            cabinets = general_cabs

        return cabinets, groups

    def get_retarget(self, cabinet, n_try=0):
        if n_try < 3:
            retarget = self._ads_response('ads.getTargetGroups', cabinet)
            if retarget:
                return retarget
            else:
                return self.get_retarget(cabinet, n_try=n_try + 1)

    def get_ads_stat(self, cabinet_id, campaign_id, client_id=None):
        ads = self._get_ads(cabinet_id, campaign_id, client_id)
        stat = self._get_ads_stat(cabinet_id, ads)
        if ads:
            return utils.get_ads_stat_summary(ads, stat)

    @staticmethod
    def get_audios_stat(audios):
        if not audios:
            return audios

        audios_with_savers = []

        # for x in range(0, len(audios), 25):
        #     y = x + 25 if x + 25 <= len(audios) else None
        #     audios_batch = audios[x:y]
        #     code = utils.code_for_get_audios_stat(audios_batch)
        #     resp = self._execute_response(code)
        #     if resp:
        #         for n, audio in enumerate(audios_batch):
        #             audios_with_savers.append({**audio, 'savers_count': resp[n]})
        #     else:
        #         audios_with_savers.extend(audios_batch)

        audio_ids = [f"{x['owner_id']}_{x['id']}" for x in audios]
        vk = AudioLikes()
        savers_count = vk.get_savers_count(audio_ids)

        if savers_count:
            for audio in audios:
                audio_id = f"{audio['owner_id']}_{audio['id']}"
                audio_savers = savers_count[audio_id] if audio_id in savers_count.keys() else 0
                audios_with_savers.append({**audio, 'savers_count': audio_savers})
        else:
            audios_with_savers = audios

        audios_with_savers = utils.simplify_vk_objs(audios_with_savers, obj_type='audio')

        return audios_with_savers

    def get_playlists_stat(self, group_id):

        resp = self._api_response('audio.getPlaylists', {'owner_id': group_id * -1, 'count': 200})
        if resp and 'items' in resp.keys():
            playlists = resp['items']
            playlists = utils.simplify_vk_objs(playlists, obj_type='playlist')
            return playlists

    def get_posts_by_ids(self, post_ids):
        posts = []
        for x in range(0, len(post_ids), 100):
            y = x + 100 if x + 100 <= len(post_ids) else None
            post_ids_batch = ','.join(post_ids[x:y])
            resp = self._api_response('wall.getById', {'posts': post_ids_batch})
            if resp:
                posts.extend(resp)
        return posts

    def get_musicians_ids(self, musicians_names):
        if isinstance(musicians_names, str):
            musicians_names = [musicians_names]

        musicians_ids = {}
        for name in musicians_names:
            resp = self._ads_response('ads.getMusicians', {'artist_name': name})
            if resp and 'items' in resp.keys():
                for x in resp['items']:
                    if x['name'] == name:
                        musicians_ids[name] = x['id']
                        break
        return musicians_ids

    def get_music_artist_formula(self, one_ad_musicians_str):
        if ', ' in one_ad_musicians_str:
            musicians = one_ad_musicians_str.split(', ')
        else:
            musicians = [one_ad_musicians_str]

        ids_dict = self.get_musicians_ids(musicians)
        if ids_dict:
            if len(ids_dict) == 1:
                return str(list(ids_dict.values())[0])
            return '&'.join([str(x) for x in ids_dict.values()])

    def get_groups_names_and_formula(self, one_ad_groups_str):
        if ', ' in one_ad_groups_str:
            groups = one_ad_groups_str.split(', ')
        else:
            groups = [one_ad_groups_str]

        group_ids, groups_dict = [], []
        for group in groups:
            group_id = utils.get_group_id_from_url(group)
            if group_id:
                group_ids.append(group_id)

        if group_ids:
            groups_dict = self._get_groups_by_ids(group_ids)

        if len(groups_dict) == 1:
            return list(groups_dict.values())[0], list(groups_dict.keys())[0]
        elif len(groups_dict) > 1:
            names = [str(x) for x in groups_dict.values()]
            ids = [str(x) for x in groups_dict.keys()]
            return ', '.join(names), '&'.join(ids)
        else:
            return None, None

    def pars_reference_post(self, post_url):
        attach_types = ['photo', 'video', 'doc', 'page', 'note', 'poll', 'album', 'market', 'market_album']
        post = self._get_post_obj(post_url)
        if post and 'attachments' in post.keys():
            text = post['text'] if 'text' in post.keys() else None
            audios = [x['audio'] for x in post['attachments'] if x['type'] == 'audio']
            playlist = self._pars_playlist(post)
            cover_url = self._get_release_cover(playlist, audios)
            attachments = [{x: utils.pars_attach_items_from_post(post, x)} for x in attach_types]
            return {'text': text,
                    'audios':  utils.simplify_vk_objs(audios, obj_type='audio'),
                    'playlist': utils.simplify_vk_objs(playlist, obj_type='playlist')[0] if playlist else None,
                    'attachments': attachments,
                    'cover_url': cover_url}

    def create_fake_group(self, group_name):
        group_id = None
        params = {'title': group_name, 'type': 'public', 'subtype': 3,
                  'public_category': 1002, 'public_subcategory': 3036}
        resp = self._api_response('groups.create', params)
        if resp and 'id' in resp.keys():
            group_id = resp['id']
            params = {'group_id': group_id, 'is_contact': 0, 'user_id': self.account.user_id}
            self._api_response('groups.editManager', params)

        if group_id:
            self._api_response('groups.edit', {'group_id': group_id, 'audio': 1})

        return group_id

    def create_campaign(self, cabinet_id, campaign_name, money_limit, client_id=None):
        data = {'type': 'promoted_posts',   # Для продвижения дарк-постов
                'name': campaign_name,      # Название кампании
                'all_limit': money_limit,   # Бюджет кампании
                'status': 1}                # 1 - запущена, 0 - остановлена

        if client_id:
            data['client_id'] = client_id

        resp = self._ads_response('ads.createCampaigns', {'account_id': cabinet_id, 'data': json.dumps([data])})
        if resp:
            return resp[0]['id']

    def create_post_replica(self, reference_orig, group_id, fake_group_id):
        reference = copy.deepcopy(reference_orig)

        if reference['audios']:
            reference = self._replicate_audios(fake_group_id, reference)
        if reference['playlist']:
            reference = self._replicate_playlist(fake_group_id, reference)

        if not reference:
            return None

        attachments = utils.get_attachments_for_post(reference)
        params = {'owner_id': group_id * -1, 'message': reference['text'], 'attachments': attachments, 'signed': 0}
        resp = self._ads_response('wall.postAdsStealth', params)
        if resp and 'post_id' in resp.keys():
            reference['owner_id'] = group_id
            reference['post_id'] = resp['post_id']
            reference['post_url'] = f"https://vk.com/wall-{group_id}_{resp['post_id']}"

        return reference

    def create_ad(self, cabinet_id, campaign_id, ad_name, post_url, sex=None, music=False, boom=False,
                  musician_formula=None, groups_formula=None, retarget_id=None, age_from=0, age_to=0,
                  age_disclaimer='0+', retarget_exclude_id=None, retarget_save_seen_id=None,
                  retarget_save_positive_id=None, retarget_save_negative_id=None):
        data = utils.data_for_create_ads(ad_name, campaign_id, post_url, sex, music, boom,
                                         musician_formula, groups_formula, retarget_id,
                                         age_from, age_to, age_disclaimer, retarget_exclude_id,
                                         retarget_save_seen_id, retarget_save_positive_id, retarget_save_negative_id)
        resp = self._ads_response('ads.createAds', {'account_id': cabinet_id, 'data': data})
        if resp:
            return resp[0]['id']

    def get_segment_size(self, cabinet_id, ad_id, post_url, client_id=None):
        params = {'account_id': cabinet_id, 'client_id': client_id, 'ad_id': ad_id, 'link_url': post_url}
        resp = self._ads_response('ads.getTargetingStats', params)
        if resp and 'audience_count' in resp.keys():
            return resp['audience_count']

    def update_ads(self, cabinet_id, ad_ids, money_limit=None, start=False, stop=False, cpm_list=None):
        datas = utils.get_data_dicts_for_update_ads(ad_ids, money_limit, start, stop, cpm_list)
        if datas:
            for x in range(0, len(datas), 5):
                y = x + 5 if x + 5 <= len(datas) else None
                data = json.dumps(datas[x:y])
                self._ads_response('ads.updateAds', {'account_id': cabinet_id, 'data': data})
                sleep(uniform(1, 4))

    def update_campaign(self, cabinet_id, campaign_id, money_limit=None, start=False, stop=False):
        data = utils.get_data_for_update_campaign(campaign_id, money_limit, start, stop)
        data = json.dumps(data)
        self._ads_response('ads.updateCampaigns', {'account_id': cabinet_id, 'data': data})

    def _replicate_playlist(self, fake_group_id, reference_orig, n_try=0):
        reference = copy.deepcopy(reference_orig)

        pl_audios = reference['playlist']['audios']
        pl_audios.reverse()
        reference['playlist']['audios'] = []
        for x in range(0, len(pl_audios), 10):
            y = x + 10 if x + 10 <= len(pl_audios) else None
            audios_batch = pl_audios[x:y]
            code = utils.code_for_add_audios_in_group(audios=audios_batch, group_id=fake_group_id)
            resp = self._execute_response(code)
            if resp:
                for n, audio_id in enumerate(resp):
                    audio = audios_batch[n]
                    audio.pop('access_key', None)
                    audio['owner_id'] = fake_group_id * -1
                    audio['audio_id'] = audio_id
                    audio['in_playlist'] = True
                    reference['playlist']['audios'].append(audio)
            else:
                if n_try < 2:
                    return self._replicate_playlist(fake_group_id, reference_orig, n_try=n_try + 1)
                else:
                    return None
            sleep(uniform(1, 4))

        pl_audios = [f"{x['owner_id']}_{x['audio_id']}" for x in reference['playlist']['audios']]
        pl_audios_str = ','.join(pl_audios)

        resp = self._api_response('audio.createPlaylist', {'owner_id': fake_group_id * -1,
                                                           'title': reference['playlist']['title']})
        if isinstance(resp, dict) and 'id' in resp.keys():
            self._api_response('audio.addToPlaylist', {'owner_id': resp['owner_id'],
                                                       'playlist_id': resp['id'],
                                                       'audio_ids': pl_audios_str})
            reference['playlist']['owner_id'] = resp['owner_id']
            reference['playlist']['playlist_id'] = resp['id']
            reference['playlist']['is_reference'] = False
            self._upload_playlist_cover(reference)
        else:
            if n_try < 2:
                return self._replicate_playlist(fake_group_id, reference_orig, n_try=n_try+1)
            else:
                return None

        return reference

    def _upload_playlist_cover(self, reference):
        if not self.playlist_cover:
            cover_url = reference['cover_url']
            self.playlist_cover = requests.get(cover_url).content

        params = {'owner_id': reference['playlist']['owner_id'], 'playlist_id': reference['playlist']['playlist_id']}
        resp = self._api_response('photos.getAudioPlaylistCoverUploadServer', params=params)
        if resp and 'upload_url' in resp.keys():
            upload_url = resp['upload_url']
            resp = requests.post(upload_url, files={'file': self.playlist_cover}).json()
            if resp and 'hash' in resp.keys() and 'photo' in resp.keys():
                img_hash, img_photo = resp['hash'], resp['photo']
                self._api_response('audio.setPlaylistCoverPhoto', params={'hash': img_hash, 'photo': img_photo})

    def _replicate_audios(self, fake_group_id, reference_orig, n_try=0):
        reference = copy.deepcopy(reference_orig)
        code = utils.code_for_add_audios_in_group(audios=reference['audios'], group_id=fake_group_id)
        resp = self._execute_response(code)
        if resp:
            for n, audio_id in enumerate(resp):
                reference['audios'][n]['owner_id'] = fake_group_id * -1
                reference['audios'][n]['id'] = audio_id
                reference['audios'][n]['in_playlist'] = False
        else:
            if n_try < 2:
                return self._replicate_audios(fake_group_id, reference_orig, n_try=n_try+1)
            else:
                return None
        return reference

    def _pars_playlist(self, post):
        playlist = utils.pars_playlists_from_post(post)
        if playlist:
            audios = self._get_playlist_audios_by_html(playlist['owner_id'], playlist['playlist_id'])
            if audios:
                resp = self._api_response('audio.getById', params={'audios': audios})
                if isinstance(resp, list) and resp:
                    audios = utils.simplify_vk_objs(resp, obj_type='audio')
                    playlist.update({'audios': audios})
                return playlist

    @staticmethod
    def _get_playlist_audios_by_html(owner_id, playlist_id):
        url = f'https://m.vk.com/audio?act=audio_playlist{owner_id}_{playlist_id}'
        page = requests.get(url).text
        soup = BeautifulSoup(page, 'lxml')
        divs = soup.find("div", class_='AudioPlaylistRoot')
        if len(divs) > 0:
            return ','.join(x['data-id'] for x in divs)

    def _get_ads(self, cabinet_id, campaign_id, client_id=None):
        params = {'account_id': cabinet_id, 'client_id': client_id,
                  'campaign_ids': json.dumps([campaign_id]), 'include_deleted': 1}
        resp = self._ads_response('ads.getAds', params)
        return resp if resp else None

    def get_campaign_status(self, cabinet_id, campaign_id, client_id=None):
        params = {'account_id': cabinet_id, 'client_id': client_id,
                  'campaign_ids': json.dumps([campaign_id]), 'include_deleted': 1}
        resp = self._ads_response('ads.getCampaigns', params)
        if isinstance(resp, list) and isinstance(resp[0], dict) and 'status' in resp[0].keys():
            return resp[0]['status'], int(resp[0]['all_limit'])
        return None, None

    def _get_ads_stat(self, cabinet_id, ads):
        if not ads:
            return None
        ad_str = ','.join([str(x['ad_id']) if 'ad_id' in x.keys() else str(x['id']) for x in ads])
        params = {'account_id': cabinet_id, 'ids': ad_str, 'ids_type': 'ad', 'period': 'overall',
                  'date_from': 0, 'date_to': 0}
        resp = self._ads_response('ads.getStatistics', params)
        if resp:
            return resp

    def _get_post_obj(self, post_url):
        post_id = utils.pars_post_id_from_post_url(post_url)
        if post_id:
            resp = self._api_response('wall.getById', {'posts': post_id})
            return resp[0] if resp else None

    def _add_audios_in_group(self, audios, group_id):
        added_audios = []
        for audio in audios:
            params = {'owner_id': audio['owner_id'], 'audio_id': audio['id'], 'group_id': group_id}
            resp = self._api_response('audio.add', params)
            if resp:
                audio = audio.copy()
                audio['owner_id'] = int(f'-{group_id}')
                audio['id'] = resp
                added_audios.append(audio)
        return added_audios

    def _get_groups_by_ids(self, group_ids):
        if len(group_ids) == 1:
            resp = self._ads_response('groups.getById', {'group_id': group_ids[0]})
        else:
            resp = self._ads_response('groups.getById', {'group_ids': ','.join(group_ids)})
        if resp:
            groups_dict = {}
            for item in resp:
                if isinstance(item, dict) and 'id' in item.keys() and 'name' in item.keys():
                    groups_dict[item['id']] = item['name']
            return groups_dict

    def _get_release_cover(self, playlist, audios):
        cover_url = None

        if playlist:
            resp = self._api_response('audio.getPlaylistById', playlist)
            if resp and 'thumbs' in resp.keys():
                cover_url = utils.get_cover_from_obj(resp['thumbs'][0])
            elif resp and 'photo' in resp.keys():
                cover_url = utils.get_cover_from_obj(resp['photo'])

        elif audios:
            for audio in audios:
                resp = self._api_response('audio.getById', {'audios': f"{audio['owner_id']}_{audio['id']}"})
                if resp and 'album' in resp[0].keys() and 'thumb' in resp[0]['album'].keys():
                    cover_url = utils.get_cover_from_obj(resp[0]['album']['thumb'])
                    break

        return cover_url
