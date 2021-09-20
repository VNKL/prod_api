import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from multiprocessing import Process, Manager
from time import sleep
from random import uniform

from api.accounts.utils import load_remixsid, release_account
from .utils import get_offset_batches, calculate_n_threads, calculate_n_threads_for_savers_count, slice_to_batches


def get_savers_list_multiprocess(audio_id, max_offset, n_threads=8):
    offset_batches = get_offset_batches(max_offset=max_offset, n_batches=n_threads)
    result_list = Manager().list()
    finished_list = Manager().list()
    for x in range(n_threads):
        finished_list.append(0)

    processes = []
    for n, offset_batch in enumerate(offset_batches):
        process = Process(target=get_savers_list_one_process,
                          args=(audio_id, offset_batch['min'], offset_batch['max'], result_list, finished_list, n))
        process.start()
        processes.append(process)
        sleep(uniform(0.5, 1))

    parsing_in_process = True
    while parsing_in_process:
        if all(finished_list):
            parsing_in_process = False
        for n, status in enumerate(finished_list):
            if status:
                processes[n].kill()
        sleep(uniform(0.5, 1))

    print('========== parsing_in_process = False ===========')

    for process in processes:
        process.kill()

    print('========== parsing processes are killed ===========')

    result = []
    for x in result_list:
        result.extend(x)

    print('========== ready to return parsing result ===========')

    return result


def get_savers_list_one_process(audio_id, offset_min, offset_max, result_list, finished_list, n_process, n_try=0):
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
        finished_list[n_process] = 1
        print(f'Process: {n_process}   |   Finished converting user_domains to user_ids')

    except Exception as err_msg:
        if n_try < 3:
            print(f'!!! error in get_savers_list_one_process in process {n_process}:', err_msg, f', n_try = {n_try}')
            get_savers_list_one_process(audio_id, offset_min, offset_max, result_list, finished_list, n_process,
                                        n_try=n_try+1)
        else:
            print(f'!!! error in get_savers_list_one_process in process {n_process}:', err_msg)

    finished_list[n_process] = 1


def get_savers_count_multiprocess(audio_ids):
    n_threads = calculate_n_threads_for_savers_count(audio_ids=audio_ids)
    if n_threads == 1:
        vk = AudioSaversNew()
        return vk.get_savers_count_one_thread(audio_ids=audio_ids)

    audios_batches = slice_to_batches(array=audio_ids, n_threads=n_threads)

    result_list = Manager().list()
    finished_list = Manager().list()
    for x in range(n_threads):
        finished_list.append(0)

    processes = []
    for n in range(n_threads):
        process = Process(target=get_savers_count_one_process,
                          args=(audios_batches[n], result_list, finished_list, n))
        process.start()
        processes.append(process)
        sleep(uniform(0.5, 1))

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

    savers_count = {}
    for x in result_list:
        savers_count.update(x)

    return savers_count


def get_savers_count_one_process(audio_ids, result_list, finish_list, n_thread):
    vk = AudioSaversNew()
    savers_count = vk.get_savers_count_one_thread(audio_ids=audio_ids)
    result_list.append(savers_count)
    finish_list[n_thread] = 1


class AudioSaversNew:

    def __init__(self):
        retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        remixsid, account = load_remixsid()
        self.remixsid = remixsid
        self.account = account
        self.request_url = 'https://m.vk.com/like'
        self.session = requests.Session()
        self.session.mount('https://m.vk.com', HTTPAdapter(max_retries=retries))
        self.session.cookies.set(name='remixsid', value=self.remixsid)

    def __del__(self):
        try:
            release_account(self.account)
        except AttributeError:
            pass

    def _get_savers_page(self, audio_id, offset=0):
        request_data = {'act': 'members', 'object': f'audio{audio_id}', 'offset': offset}
        with self.session.post(self.request_url, params=request_data) as resp:
            return resp.text

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

    def get_savers_count_one_thread(self, audio_ids):
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

    @staticmethod
    def get_savers_count(audio_ids):
        return get_savers_count_multiprocess(audio_ids)

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

    def pars_savers_one_page(self, audio_id, offset):
        try:
            page = self._get_savers_page(audio_id=audio_id, offset=offset)
            users, _ = self._get_users_from_page(page=page, audio_id=audio_id)
            return users
        except Exception as err_msg:
            print('!!! pars_savers_one_page error:', err_msg)
            return []
