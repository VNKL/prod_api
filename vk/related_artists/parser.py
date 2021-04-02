import requests

from time import sleep
from datetime import datetime
from random import uniform
from python_rucaptcha import ImageCaptcha


import utils
from vk.engine import VkEngine


def _pars_feats_from_audios(audios, main_artist_name):
    """
    Возвращает дикт с именами и каталожными айдишками артистов, с которыми были фиты

    :param audios:              list, список с объектами аудиозаписей ВК
    :param main_artist_name:    str, имя основного артиста
    :return:                    dict, {artist_name, artist_id}
    """
    feat_artists_ids = {}
    for audio in audios:
        if 'main_artists' in audio.keys():
            for artist in audio['main_artists']:
                if artist['name'] != main_artist_name:
                    try:
                        feat_artists_ids[artist['name']] = artist['id']
                    except KeyError:
                        pass
        if 'featured_artists' in audio.keys():
            for artist in audio['featured_artists']:
                if artist['name'] != main_artist_name:
                    try:
                        feat_artists_ids[artist['name']] = artist['id']
                    except KeyError:
                        pass
    return feat_artists_ids


def _listens_threshold_passed(artist_card_item, listens_threshold, n_last_releases):
    """
    Возвращает True или False, если артист проходт или не прохождит порог
    по прослушиваниям на N последних релизных плейлистах

    :param artist_card_item:    dict, объект карточки артиста, разобранный из JSON-ответа ВК
    :param listens_threshold:   int, минимальный порог по прослушиваниям в среднем по релизам
    :param n_last_releases:     int, количество последних релизов для анализа
    :return:                    bool, True - порог пройден, False - не пройден
    """

    if 'playlists' not in artist_card_item.keys():
        return False

    playlists = artist_card_item['playlists']

    if len(playlists) <= n_last_releases:
        listens = sum([x['plays'] for x in playlists]) / len(playlists)
    else:
        listens = sum([x['plays'] for x in playlists[:n_last_releases]]) / n_last_releases

    return True if listens > listens_threshold else False


def _is_artist_alive(artist_card_item, days_from_last_release):
    """
    Возвращает True или False, если артист жив или мертв
    Имеется ввиду, если в споследнего релиза прошло больше дней, чем хотелось бы

    :param artist_card_item:        dict, разобранный JSON объект карточки основного артиста
    :param days_from_last_release:  int, максиально допустимое кол-во дней, прошедших от даты последнего релиза
    :return:                        bool, True - проверка пройдена, False - не пройдена
    """

    if 'playlists' not in artist_card_item.keys():
        return False

    last_release_timestamp = artist_card_item['playlists'][0]['create_time']
    last_release_datetime = datetime.fromtimestamp(last_release_timestamp)

    now_datetime = datetime.now()

    days_delta = (now_datetime - last_release_datetime).days

    return True if days_delta <= days_from_last_release else False


class RelatedArtistsParser(VkEngine):

    def get_from_artist_url(self, artist_card_url, max_recurse=3, n_releases=3, include_feats=False,
                            min_listens=None, days_from_last_release=None):

        related_urls, related_cards = [], []

        related_block_id = self._get_related_block_id(id_or_url=artist_card_url)
        if related_block_id:
            related_urls.extend(self._pars_related_block(block_id=related_block_id))
        else:
            self.errors.append({'method': 'api/relateds/get_from_artist_url', 'param': artist_card_url,
                                'error_msg': 'Artis card have no related artists'})
        if related_urls:
            related_cards.extend(self._get_related_cards(related_urls=related_urls))

    def _get_related_block_id(self, id_or_url):
        params = {'url': id_or_url} if 'vk.com' in id_or_url else {'artist_id': id_or_url}
        params.update({'need_blocks': 1})
        resp = self._api_response('catalog.getAudioArtist', params)
        if resp:
            if '{artist_name}' not in resp['catalog']['sections'][0]['title']:
                return utils.find_related_block_id(resp['catalog']['sections'][0]['blocks'])
            else:
                self.errors.append({'method': 'api/relateds/get_from_artist_url', 'param': id_or_url,
                                    'error_msg': 'Artist card is not found'})

    def _pars_related_block(self, block_id, next_from=None):
        related_urls = []
        resp = self._api_response('catalog.getBlockItems', {'block_id': block_id, 'start_from': next_from})
        if resp:
            for link in resp['links']:
                related_urls.append({'artist': link['title'], 'url': link['url']})
            if 'next_from' in resp['block'].keys():
                related_urls.extend(self._pars_related_block(block_id=block_id, next_from=resp['block']['next_from']))
        return related_urls

    def _get_related_cards(self, related_urls):
        cards = []
        code = utils.code_for_get_artist_cards_from_urls(urls_list=related_urls)
        execute_resp = self._execute_response(code)
        if execute_resp:
            for x in execute_resp:
                print(x)

        return cards








class VkArtistCards:

    def __init__(self, token, rucaptcha_key, proxy=None):
        """
        Класс для работы с картчоками артистов

        :param token:           str, токен от ВК
        :param rucaptcha_key:   str, ключ от аккаунта рукапчи
        :param proxy:           str, прокся в формате login:pass@ip:port
        """

        self.token = token
        self.rucaptcha_key = rucaptcha_key
        self.proxy = {'https': f'https://{proxy}'} if proxy else None
        self.session = requests.session()
        self.failed_artists = []
        self.parsed_cards_urls = {}

    def _anticaptcha(self, captcha_img):
        """
        Функция для работы с API рукапчи

        :param captcha_img:         str ссылка на изображение капчи
        :return:                    str разгаданная капча
        """

        user_answer = ImageCaptcha.ImageCaptcha(rucaptcha_key=self.rucaptcha_key).captcha_handler(
            captcha_link=captcha_img)
        captcha_key = user_answer['captchaSolve']

        return captcha_key

    def _resp_with_anticaptcha(self, url, captcha_sid=None, captcha_key=None):
        if captcha_sid and captcha_key:
            url = f'{url}&captcha_sid={captcha_sid}&captcha_key={captcha_key}'
        resp = self.session.get(url, proxies=self.proxy).json()
        if 'error' in resp.keys():
            if resp['error']['error_msg'] == 'Captcha needed':
                captcha_sid = resp['error']['captcha_sid']
                captcha_img = resp['error']['captcha_img']
                captcha_key = self._anticaptcha(captcha_img)
                return self._resp_with_anticaptcha(url, captcha_sid, captcha_key)
            else:
                return resp
        else:
            return resp

    def get_related_artists(self, artist_card_url, include_feats=False, csv_path=None, max_recurse_level=3,
                            listens_threshold=None, n_last_releases=3, days_from_last_release=None):
        """
        Возвращает дикт с похожими артистами и ссылками на их карточки в ВК

        :param artist_card_url:         str - ссылка на карточку артиста в ВК
        :param include_feats:           bool, True - парсить артистов из фитов в качестве похожих, False - нет
        :param csv_path:                str, путь к csv файлу для записи результатов в реальном времени
        :param max_recurse_level:       int, максимальный уровень рекурсии по карточкам похожих артистов
        :param listens_threshold:       int, минимальный порог по прослушиваниям в среднем по релизам
        :param n_last_releases:         int, количество последних релизов для анализа
        :param days_from_last_release:  int, максиально допустимое кол-во дней, прошедших от даты последнего релиза
        :return:                        dict, {artist_name, artist_card_url}
        """
        # Проверка на дурака
        artist_card_id = self._get_artist_card_id(artist_id_or_card_url=artist_card_url)
        if not artist_card_id:
            return None

        self._recurse_artist_card(artist_card_id=artist_card_id,
                                  include_feats=include_feats,
                                  csv_path=csv_path,
                                  max_recurse_level=max_recurse_level,
                                  listens_threshold=listens_threshold,
                                  n_last_releases=n_last_releases,
                                  days_from_last_release=days_from_last_release)

        return self.parsed_cards_urls

    def _recurse_artist_card(self, artist_id=None, artist_card_id=None, artist_name=None, include_feats=False,
                             csv_path=None, max_recurse_level=3, current_recurse_level=0, listens_threshold=None,
                             n_last_releases=3, days_from_last_release=None):
        """
        Рекрсивно проходит по всем похожим артистам всех похожих артистов, начиная с основного артиста.
        Результат записывается в аргумент parsed_cards_urls объекта

        :param artist_id:           int, айди артиста
        :param artist_card_id:      str, айди карточки артиста
        :param artist_card_id:      str, имя артиста (для пополнения списка фейлов)
        :param include_feats:       bool, True - парсить артистов из фитов в качестве похожих, False - нет
        :param csv_path:            str, путь к csv файлу для записи результатов в реальном времени
        :param max_recurse_level:   int, максимальный уровень рекурсии по карточкам похожих артистов
        :param listens_threshold:   int, минимальный порог по прослушиваниям в среднем по релизам
        :param n_last_releases:     int, количество последних релизов для анализа
        :param days_from_last_release:  int, максиально допустимое кол-во дней, прошедших от даты последнего релиза
        """
        # Если ничего не передано - райзим исключение
        if not artist_id and not artist_card_id:
            raise RuntimeError("don't passed artist_id or artist_card_id")

        # Если не передан айди карточки артиста, получаем его из айди артиста
        if not artist_card_id:
            artist_card_id = self._get_artist_card_id(artist_id_or_card_url=artist_id)

        # Если у артиста есть карточка (если она нашлась)
        if artist_card_id:
            artist_card_item = self._get_artist_card_item(artist_card_id=artist_card_id)
            related_artists = self._pars_artist_card(artist_card_item=artist_card_item,
                                                     include_feats=include_feats,
                                                     csv_path=csv_path,
                                                     listens_threshold=listens_threshold,
                                                     n_last_releases=n_last_releases,
                                                     days_from_last_release=days_from_last_release)
            if related_artists:
                for related_artist_name, related_artist_id in related_artists.items():
                    if related_artist_name not in self.parsed_cards_urls.keys() and \
                            related_artist_name not in self.failed_artists:
                        sleep(uniform(0.4, 0.5))
                        if current_recurse_level < max_recurse_level:
                            print(f'recurse level: {current_recurse_level}\t | \t\t'
                                  f'scanned artist: {related_artist_name}')
                            self._recurse_artist_card(artist_id=related_artist_id,
                                                      artist_name=related_artist_name,
                                                      include_feats=include_feats,
                                                      csv_path=csv_path,
                                                      max_recurse_level=max_recurse_level,
                                                      current_recurse_level=current_recurse_level+1,
                                                      listens_threshold=listens_threshold,
                                                      n_last_releases=n_last_releases,
                                                      days_from_last_release=days_from_last_release)
                        else:
                            print(f'recurse level: {current_recurse_level}\t | \t\t'
                                  f'scanned artist: {related_artist_name}')
                            related_artist_card_id = self._get_artist_card_id(artist_id_or_card_url=related_artist_id)
                            related_artist_card_item = self._get_artist_card_item(artist_card_id=related_artist_card_id)
                            self._pars_artist_card(artist_card_item=related_artist_card_item,
                                                   include_feats=include_feats,
                                                   csv_path=csv_path,
                                                   listens_threshold=listens_threshold,
                                                   n_last_releases=n_last_releases,
                                                   days_from_last_release=days_from_last_release)
        else:
            self.failed_artists.append(artist_name)

    def _pars_artist_card(self, artist_card_item, include_feats=False, csv_path=None, listens_threshold=None,
                          n_last_releases=3, days_from_last_release=None):
        """
        Возвращает дикт с похожими артистами и их айдишками.
        Артисты берутся из фитов и блока с похожими артистами в карточке основного артиста.
        Обновляет аргумент parsed_cards_urls объекта

        :param artist_card_item:        dict, разобранный JSON объект карточки основного артиста
        :param include_feats:           bool, True - парсить артистов из фитов в качестве похожих, False - нет
        :param csv_path:                str, путь к csv файлу для записи результатов в реальном времени
        :param listens_threshold:       int, минимальный порог по прослушиваниям в среднем по релизам
        :param n_last_releases:         int, количество последних релизов для анализа
        :param days_from_last_release:  int, максиально допустимое кол-во дней, прошедших от даты последнего релиза
        :return:                        dict, {artist_name, artist_id (or artist_card_url)}
        """
        # Если такого ключа нет, то нет карточки артиста
        if not artist_card_item or 'artists' not in artist_card_item.keys():
            return None

        # Достаем инфу об основном артисте переданной карточки артиста
        card_artist_name = artist_card_item['artists'][0]['name']
        card_url = artist_card_item['section']['url']
        finded_artists = {card_artist_name: card_url}

        # Проверка на повторы
        if card_artist_name in self.parsed_cards_urls.keys():
            return None

        # Проверка на прохождение всех переданных фильтров
        self._artist_parameters_filter(artist_card_item, card_artist_name, card_url, csv_path, days_from_last_release,
                                       listens_threshold, n_last_releases)

        if include_feats and 'audios' in artist_card_item.keys():
            finded_artists.update(_pars_feats_from_audios(audios=artist_card_item['audios'],
                                                          main_artist_name=card_artist_name))

        # Поиск блока с похожими артистами (его может не быть)
        related_artists_block_id = None
        for block in artist_card_item['section']['blocks']:
            if 'url' in block.keys() and 'related' in block['url']:
                related_artists_block_id = block['id']

        if related_artists_block_id:
            finded_artists.update(self._pars_related_artists_block(related_artists_block_id=related_artists_block_id))

        return finded_artists

    def _artist_parameters_filter(self, artist_card_item, card_artist_name, card_url, csv_path, days_from_last_release,
                                  listens_threshold, n_last_releases):
        """
        Проверяет карточку артиста на прохождение всех переданных фильтров, а именно:
            - среднее кол-во прослушиваний на N последних релизных плейлистах
            - дата последнего релиза

        Записывает артиста в соответствующие аргументы объекта осле прохождения всех фильтров

        """
        # Если переданы порог прослушиваний и дни от последнего релиза
        if listens_threshold and days_from_last_release:
            if _listens_threshold_passed(artist_card_item=artist_card_item,
                                         listens_threshold=listens_threshold,
                                         n_last_releases=n_last_releases):
                if _is_artist_alive(artist_card_item=artist_card_item,
                                    days_from_last_release=days_from_last_release):
                    self.parsed_cards_urls[card_artist_name] = card_url
                    if csv_path:
                        with open(csv_path, 'a', encoding='utf-16') as file:
                            file.write(f'{card_artist_name}\t{card_url}\n')
                else:
                    self.failed_artists.append(card_artist_name)
            else:
                self.failed_artists.append(card_artist_name)

        # Если передан только порог по прослушивнаиям
        elif listens_threshold:
            if _listens_threshold_passed(artist_card_item=artist_card_item,
                                         listens_threshold=listens_threshold,
                                         n_last_releases=n_last_releases):
                self.parsed_cards_urls[card_artist_name] = card_url
                if csv_path:
                    with open(csv_path, 'a', encoding='utf-16') as file:
                        file.write(f'{card_artist_name}\t{card_url}\n')
            else:
                self.failed_artists.append(card_artist_name)

        # Если переданы только дни от последнего релиза
        elif days_from_last_release:
            if _is_artist_alive(artist_card_item=artist_card_item,
                                days_from_last_release=days_from_last_release):
                self.parsed_cards_urls[card_artist_name] = card_url
                if csv_path:
                    with open(csv_path, 'a', encoding='utf-16') as file:
                        file.write(f'{card_artist_name}\t{card_url}\n')
            else:
                self.failed_artists.append(card_artist_name)

        # Если ничего не передано
        else:
            self.parsed_cards_urls[card_artist_name] = card_url
            if csv_path:
                with open(csv_path, 'a', encoding='utf-16') as file:
                    file.write(f'{card_artist_name}\t{card_url}\n')

    def _pars_related_artists_block(self, related_artists_block_id):
        """
        Возвращает дикт с именами и каталожными айдишками артистов из блока похожих артистов в карточке артиста

        :param related_artists_block_id:    str, айди блока похожих артистов
        :return:                            dict, {artist_name, artist_card_url}
        """
        url = f'https://api.vk.com/method/catalog.getBlockItems?v=5.96&access_token={self.token}&' \
              f'block_id={related_artists_block_id}'
        resp = self._resp_with_anticaptcha(url)

        try:
            related_artists_ids = {artist['title']: artist['url'] for artist in resp['response']['links']}
        except KeyError:
            sleep(uniform(0.4, 0.5))
            return self._pars_related_artists_block(related_artists_block_id=related_artists_block_id)

        if 'next_from' in resp['response']['block'].keys():
            url += f"&start_from={resp['response']['block']['next_from']}"
            resp = self._resp_with_anticaptcha(url)
            # По некст фрому может ничего не вернуться, точнее в таком сулчае вернется error
            if 'response' in resp.keys():
                related_artists_ids.update({artist['title']: artist['url'] for artist in resp['response']['links']})

        return related_artists_ids

    def _get_artist_card_item(self, artist_card_id):
        """
        Возвращает декодированный в дикт JSON-объект карточки артиста

        :param artist_card_id:  str, айди карточки артиста
        :return:                dict, объект карточки артиста
        """
        url = f'https://api.vk.com/method/catalog.getSection?v=5.96&access_token={self.token}&' \
              f'section_id={artist_card_id}'
        resp = self._resp_with_anticaptcha(url)
        if isinstance(resp, dict) and 'response' in resp.keys():
            return resp['response']

    def _get_artist_card_id(self, artist_id_or_card_url):
        """
        Возвращает айди карточки артиста по ссылке на эту карточку или айдишке артсита.
        Либо возвращает None, если карточка не найдена

        :param artist_id_or_card_url:       str or int, ссылка на карточку артиста в ВК
        :return:                            str or None
        """
        # Проверка на тип переменной и выбор соответствующего параметра для метода API
        if 'vk.com' in artist_id_or_card_url:
            url = f'https://api.vk.com/method/catalog.getAudioArtist?v=5.96&access_token={self.token}&' \
                  f'url={artist_id_or_card_url}'
        else:
            url = f'https://api.vk.com/method/catalog.getAudioArtist?v=5.96&access_token={self.token}&' \
                  f'artist_id={artist_id_or_card_url}'

        resp = self._resp_with_anticaptcha(url)
        try:
            if '{artist_name}' in resp['response']['catalog']['sections'][0]['title']:
                return None
            return resp['response']['catalog']['sections'][0]['id']
        except KeyError:
            print(resp)
            return None

