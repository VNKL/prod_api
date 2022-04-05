from multiprocessing import Process, Manager
from random import uniform
from time import sleep

from vk.engine import VkEngine
from .utils import code_for_savers_count, need_execute
from vk.audio_savers_new.utils import calculate_n_threads_for_savers_count, slice_to_batches


def get_savers_count_multiprocess(audio_ids, n_threads):
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
    vk = AudioLikes()
    savers_count = vk.get_savers_count_one_thread(audio_ids=audio_ids)
    result_list.append(savers_count)
    finish_list[n_thread] = 1


class AudioLikes(VkEngine):

    def _sc_for_one_audio(self, full_audio_id: str):
        owner_id, audio_id = full_audio_id.split('_')
        if need_execute(audio_id=full_audio_id):
            code = code_for_savers_count(owner_id=owner_id, audio_id=audio_id)
            resp = self._execute_response(code=code)
            if resp and isinstance(resp, int):
                return resp
        else:
            data = {'type': 'audio', 'owner_id': owner_id, 'item_id': audio_id}
            resp = self._api_response(method='likes.add', params=data)
            if isinstance(resp, dict) and 'likes' in resp.keys():
                return resp['likes']

    def get_savers_count_one_thread(self, audio_ids):
        if isinstance(audio_ids, str):
            audio_ids = [audio_ids]
        elif isinstance(audio_ids, list):
            audio_ids = audio_ids
        else:
            raise TypeError('audio_id must be str or list')

        savers_count = {}
        for audio_ids in audio_ids:
            sc = self._sc_for_one_audio(full_audio_id=audio_ids)
            savers_count[audio_ids] = sc

        return savers_count

    def get_savers_count(self, audio_ids):
        n_threads = calculate_n_threads_for_savers_count(audio_ids=audio_ids)
        if n_threads == 1:
            return self.get_savers_count_one_thread(audio_ids=audio_ids)

        return get_savers_count_multiprocess(audio_ids, n_threads)
