from time import sleep
from multiprocessing import Process, Manager

from vk.users_audios import utils
from vk.engine import VkEngine


def get_audios_multiprocess(user_ids, n_last):
    if len(user_ids) > 10000:
        user_ids = user_ids[:10000]

    d = int(len(user_ids) / 8)
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
    vk = UserAudiosParser()
    audios = vk.get_audios_one_thread(user_ids, n_last)
    result_list.extend(audios)


class UserAudiosParser(VkEngine):

    def get(self, user_ids, n_last, get_type='tracks'):
        if get_type not in ['tracks', 'artists']:
            raise ValueError("type must be 'tracks' or 'artists'")

        if len(user_ids) > 10000:
            user_ids = user_ids[:10000]

        audios = get_audios_multiprocess(user_ids, n_last)
        return self.calculate_items(audios, get_type)

    def calculate_items(self, audios, get_type):
        if get_type == 'tracks':
            simplify = utils.audios_to_tracks
        elif get_type == 'artists':
            simplify = utils.audios_to_artists
        else:
            return []

        items = simplify(audios)
        return utils.calculate_counts(items)

    def get_audios_one_thread(self, user_ids, n_last):
        if len(user_ids) > 10000:
            user_ids = user_ids[:10000]

        audios = []
        for x in range(0, len(user_ids), 25):
            y = x + 25 if x + 25 <= len(user_ids) else None
            code = utils.code_for_get_user_audios(user_ids[x:y], n_last)
            resp = self._execute_response(code)
            audios.extend(utils.unpack_resp(resp))

        return audios
