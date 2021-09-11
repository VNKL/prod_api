import requests
from bs4 import BeautifulSoup
from multiprocessing import Process, Manager
from time import sleep
from random import uniform

from api.accounts.utils import load_remixsid, release_account
from .utils import get_offset_batches, calculate_n_threads


def get_savers_list_multiprocess(audio_id, max_offset, n_threads=8):
    offset_batches = get_offset_batches(max_offset=max_offset, n_batches=n_threads)
    result_list = Manager().list()
    finished_list = Manager().list()
    processes = []
    for n, offset_batch in enumerate(offset_batches):
        process = Process(target=get_savers_list_one_process,
                          args=(audio_id, offset_batch['min'], offset_batch['max'], result_list, finished_list, n))
        process.start()
        processes.append(process)
        sleep(uniform(1, 2))

    parsing_in_process = True
    while parsing_in_process:
        is_finished = _check_processes_finish(finished_list, n_threads)
        if is_finished:
            parsing_in_process = False
        sleep(uniform(1, 2))

    for process in processes:
        process.kill()

    result = []
    for x in result_list:
        result.extend(x)

    return result


def get_savers_list_one_process(audio_id, offset_min, offset_max, result_list, finished_list, n_process):
    try:
        vk = AudioSaversNew()
        savers_list = vk.pars_savers_one_thread(audio_id=audio_id,
                                                offset_from=offset_min,
                                                offset_to=offset_max,
                                                n_thread=n_process)

        print(f'Process: {n_process}   |   Starting converting user_domains to user_ids')
        from vk.audio_savers.parser import AudioSaversParser
        vk = AudioSaversParser()
        ids_dict = vk.get_user_ids_from_domains(domains=savers_list)
        ids_list = list(ids_dict.values())
        result_list.append(ids_list)
        print(f'Process: {n_process}   |   Finished converting user_domains to user_ids')
    except Exception as err_msg:
        print(f'!!! error in get_savers_list_one_process in process {n_process}', err_msg)
    finished_list.append(n_process)


def _check_processes_finish(finished_list, n_threads):
    if len(finished_list) == n_threads:
        return True


class AudioSaversNew:

    def __init__(self):
        remixsid, account = load_remixsid()
        self.remixsid = remixsid
        self.account = account

    def __del__(self):
        try:
            release_account(self.account)
        except AttributeError:
            pass

    def _get_savers_page(self, audio_id, offset=0):
        request_url = 'https://m.vk.com/like'
        request_data = {'act': 'members', 'object': f'audio{audio_id}', 'offset': offset}
        page = requests.post(request_url, cookies={'remixsid': self.remixsid}, params=request_data).text
        return page

    @staticmethod
    def _get_users_from_page(page, audio_id):
        soup = BeautifulSoup(page, 'lxml')
        a_hrefs = [x['href'] for x in soup.find_all('a')]
        if '/menu' in a_hrefs:
            slice_start = a_hrefs.index('/menu')
        elif '/join' in a_hrefs:
            slice_start = a_hrefs.index('/join')
        elif len(a_hrefs) > 1:
            slice_start = 1
        else:
            slice_start = 0
        slice_end = None
        max_offset = 0

        pagination = f'/like?act=members&object=audio{audio_id}&offset=0'
        if pagination in a_hrefs:
            slice_end = a_hrefs.index(pagination)
            max_offset = a_hrefs[-1].replace(pagination[:-1], '')
            max_offset = int(max_offset)

        users_hrefs = a_hrefs[slice_start + 1: slice_end]
        users = [x[1:] for x in users_hrefs]

        return users, max_offset

    def _get_savers_count_for_one_audio(self, audio_id):
        page = self._get_savers_page(audio_id)
        soup = BeautifulSoup(page, 'lxml')
        a_hrefs = [x['href'] for x in soup.find_all('a')]
        slice_start, slice_end = a_hrefs.index('/menu'), None

        pagination = f'/like?act=members&object=audio{audio_id}&offset=0'
        max_offset = a_hrefs[-1].replace(pagination[:-1], '') if pagination in a_hrefs else 0

        if max_offset:
            page = self._get_savers_page(audio_id=audio_id, offset=max_offset)
            soup = BeautifulSoup(page, 'lxml')
            a_hrefs = [x['href'] for x in soup.find_all('a')]
            slice_start, slice_end = a_hrefs.index('/menu'), a_hrefs.index(pagination)

        users_hrefs = a_hrefs[slice_start + 1: slice_end]

        return int(max_offset) + len(users_hrefs)

    def get_savers_count(self, audio_ids):
        if not self.remixsid:
            return None

        if isinstance(audio_ids, str):
            audio_ids = [audio_ids]
        elif isinstance(audio_ids, list):
            audio_ids = audio_ids
        else:
            raise TypeError('audio_id must be str or list')

        savers_count = {}
        for audio_ids in audio_ids:
            sc = self._get_savers_count_for_one_audio(audio_id=audio_ids)
            savers_count[audio_ids] = sc

        return savers_count

    def get_savers_list(self, audio_id):
        page = self._get_savers_page(audio_id=audio_id)
        users, max_offset = self._get_users_from_page(page=page, audio_id=audio_id)

        from vk.audio_savers.parser import AudioSaversParser
        vk = AudioSaversParser()
        ids_dict = vk.get_user_ids_from_domains(domains=users)
        users = list(ids_dict.values())

        n_threads = calculate_n_threads(max_offset=max_offset)

        if max_offset:
            users.extend(get_savers_list_multiprocess(audio_id=audio_id, max_offset=max_offset, n_threads=n_threads))

        return users

    def pars_savers_one_thread(self, audio_id, offset_from, offset_to, n_thread=1):
        users = []
        for offset in range(offset_from, offset_to + 50, 50):
            page = self._get_savers_page(audio_id=audio_id, offset=offset)
            try:
                next_users, _ = self._get_users_from_page(page=page, audio_id=audio_id)
                users.extend(next_users)
                print(f'Process: {n_thread}   |   Offset: {offset} / {offset_to}')
            except Exception as err_msg:
                print('!!! pars_savers_one_thread error', err_msg)

        print(f'Process: {n_thread}   |   Parsing is finished')

        return users
