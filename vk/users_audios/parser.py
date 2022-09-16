from multiprocessing import Manager, Process
from time import sleep

from vk_api import VkApi
from vk_api.audio import VkAudio
from vk_api.exceptions import AuthError, AccessDenied, Captcha

from vk.users_audios import utils
from api.accounts.utils import load_account, release_account
from api.settings import RUCAPTCHA_KEY
from vk.engine import anticaptcha


def get_audios_multiprocess(user_ids, n_last):
    if len(user_ids) > 500:
        user_ids = user_ids[:500]

    d = int(len(user_ids) / 4)
    d = 1 if d == 0 else d
    ids_batches = []
    for x in range(0, len(user_ids), d):
        y = x + d if x + d <= len(user_ids) else None
        ids_batches.append(user_ids[x:y])

    parser_manager = Manager()
    result_list = parser_manager.list()
    processes = [Process(target=_pars_audios_batch, args=(x, n_last, result_list)) for x in ids_batches]
    for p in processes:
        p.start()
        sleep(1)
    for p in processes:
        p.join()

    result_list = list(result_list)
    return result_list


def _pars_audios_batch(user_ids, n_last, result_list):
    vk = UserAudiosParserThread()
    audios = vk.get(user_ids, n_last)
    result_list.extend(audios)


# class UserAudiosParser(VkEngine):
#
#     def get(self, user_ids, n_last, get_type='tracks'):
#         if get_type not in ['tracks', 'artists']:
#             raise ValueError("type must be 'tracks' or 'artists'")
#
#         if len(user_ids) > 10000:
#             user_ids = user_ids[:10000]
#
#         audios = get_audios_multiprocess(user_ids, n_last)
#         return self.calculate_items(audios, get_type)
#
#     def calculate_items(self, audios, get_type):
#         if get_type == 'tracks':
#             simplify = utils.audios_to_tracks
#         elif get_type == 'artists':
#             simplify = utils.audios_to_artists
#         else:
#             return []
#
#         items = simplify(audios)
#         return utils.calculate_counts(items)
#
#     def get_audios_one_thread(self, user_ids, n_last):
#         if len(user_ids) > 10000:
#             user_ids = user_ids[:10000]
#
#         audios = []
#         for x in range(0, len(user_ids), 25):
#             y = x + 25 if x + 25 <= len(user_ids) else None
#             code = utils.code_for_get_user_audios(user_ids[x:y], n_last)
#             resp = self._execute_response(code)
#             audios.extend(utils.unpack_resp(resp))
#
#         return audios


def captcha_handler(captcha):
    url = captcha.get_url()
    key = anticaptcha(captcha_img=url, rucaptcha_key=RUCAPTCHA_KEY)
    return captcha.try_again(key)


class UserAudiosParser:

    def get(self, user_ids, n_last, get_type='tracks'):
        if get_type not in ['tracks', 'artists']:
            print('false type')
            raise ValueError("type must be 'tracks' or 'artists'")

        if len(user_ids) > 500:
            user_ids = user_ids[:500]

        if n_last > 100:
            n_last = 100

        audios = get_audios_multiprocess(user_ids, n_last)
        return self.calculate_items(audios, get_type)

    @staticmethod
    def calculate_items(audios, get_type):
        if get_type == 'tracks':
            simplify = utils.audios_to_tracks
        elif get_type == 'artists':
            simplify = utils.audios_to_artists
        else:
            return []

        items = simplify(audios)
        return utils.calculate_counts(items)


class UserAudiosParserThread:

    def __init__(self):
        self.account = load_account()
        self.vk = VkApi(login=self.account.login, password=self.account.password, captcha_handler=captcha_handler)
        self._auth()
        self.vk_audio = VkAudio(self.vk)

    def __del__(self):
        try:
            release_account(self.account)
        except AttributeError:
            pass

    def _auth(self):
        try:
            self.vk.auth()
        except AuthError:
            false_acc = self.account
            self.account = load_account()
            self.vk = VkApi(login=self.account.login, password=self.account.password, captcha_handler=captcha_handler)
            self._auth()
            release_account(false_acc)

    def get(self, user_ids, n_last):
        all_users_audios = []
        for user_id in user_ids:
            user_audios = self.get_iter(user_id=user_id, n_last=n_last)
            if user_audios:
                all_users_audios.append(user_audios)

        return all_users_audios

    def get_iter(self, user_id, n_last):
        audios = []
        try:
            audios_iter = self.vk_audio.get_iter(owner_id=user_id)
            for n, audio in enumerate(audios_iter):
                audios.append(audio)
                n += 1
                if n >= n_last:
                    break
        except AccessDenied:
            print(f'Access to id{user_id} audios denied')
        return audios
