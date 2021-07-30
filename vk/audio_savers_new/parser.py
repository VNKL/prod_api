import requests
from bs4 import BeautifulSoup

from api.accounts.utils import load_remixsid, release_account


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
        slice_start, slice_end = a_hrefs.index('/menu'), None
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

    def get_savers_count(self, audio_id):

        if not self.remixsid:
            return None

        if isinstance(audio_id, str):
            audio_ids = [audio_id]
        elif isinstance(audio_id, list):
            audio_ids = audio_id
        else:
            raise TypeError('audio_id must be str or list')

        savers_count = {}
        for audio_id in audio_ids:
            sc = self._get_savers_count_for_one_audio(audio_id=audio_id)
            savers_count[audio_id] = sc

        return savers_count

    # def get_savers_list(self, audio_id):
    #     page = self._get_savers_page(audio_id=audio_id)
    #     users, max_offset = self._get_users_from_page(page=page, audio_id=audio_id)
    #
    #     if max_offset:
    #         try:
    #             for offset in range(50, max_offset + 50, 50):
    #                 page = self._get_savers_page(audio_id=audio_id, offset=offset)
    #                 next_users, _ = self._get_users_from_page(page=page, audio_id=audio_id)
    #                 users.extend(next_users)
    #         except Exception:
    #             pass
    #
    #     return users
