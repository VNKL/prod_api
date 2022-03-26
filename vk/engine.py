""" Use Python 3.7 """
import json

import requests

from random import uniform
from time import sleep
from python_rucaptcha import ImageCaptcha

from api.accounts.utils import load_account, mark_account_dead, mark_account_rate_limited, release_account, \
    load_proxy, release_proxy
from api.settings import VK_API_VERSION, RUCAPTCHA_KEY, EXECUTE_FALSES_METHODS


API_SLEEPING_ERRORS = [1, 6, 10]        # Ошибка АПИ ВК, для которых просят тповторить запрос позже
TOKEN_FATAL_ERRORS = [4, 5, 17, 5]      # Ошибки АПИ ВК, связанные с потерей аккаунта
TOKEN_SLEEPING_ERRORS = [9, 29]         # Ошибки АПИ ВК, связанные с заморозкой токена на определенный метод


def anticaptcha(captcha_img, rucaptcha_key):
    """
    Функция для работы с API рукапчи

    :param captcha_img:         str, ссылка на изображение капчи
    :param rucaptcha_key:       str, ключ от аккаунта на рукапче
    :return:                    str, разгаданная капча
    """
    user_answer = ImageCaptcha.ImageCaptcha(rucaptcha_key=rucaptcha_key).captcha_handler(
        captcha_link=captcha_img)
    captcha_key = user_answer['captchaSolve']

    return captcha_key


class VkEngine:

    def __init__(self):
        self.account = load_account()
        self.proxy = None
        self.errors = []
        self.n_try = 0

    def __del__(self):
        try:
            release_account(self.account)
        except AttributeError:
            pass

    def _get_api_response(self, url, data, captcha_sid=None, captcha_key=None):
        """
        Возвращает ответ апи ВК, отбиваясь от капчи и ту мэни реквестс пер секонд

        :param url:             str, урл запроса к апи с названием метода (без параметров!!!)
        :param data:            dict, дикт с параметрами метода
        :param captcha_sid:     str, сид капчи
        :param captcha_key:     str, разгаданная капча
        :return:                dict, разобранный из JSON ответ апи ВК (None - если ошибка в ответе)
        """
        sleep(uniform(0.4, 0.6))

        proxy_dict = {'https': f'http://{self.proxy}'} if self.proxy else None

        if captcha_sid and captcha_key:
            if data:
                data.update({'captcha_sid': captcha_sid, 'captcha_key': captcha_key})
            else:
                data = {'captcha_sid': captcha_sid, 'captcha_key': captcha_key}

        try:
            resp = requests.post(url, data, proxies=proxy_dict).json()
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            return self._handle_requests_error(url, data, captcha_sid, captcha_key)
        except json.decoder.JSONDecodeError:
            return self._handle_json_error(url, data, captcha_sid, captcha_key)

        if 'execute_errors' in resp.keys():
            return self._handle_execute_errors(url, data, captcha_sid, captcha_key, resp)

        if 'error' in resp.keys():
            return self._handle_api_error(captcha_key, captcha_sid, data, resp, url)
        else:
            return resp['response']

    def _handle_json_error(self, url, data, captcha_sid, captcha_key):
        if self.n_try < 10:
            return self._get_api_response(url, data, captcha_sid, captcha_key)
        else:
            self.errors.append({'error_msg': 'VK API request max retries error (json.decoder.JSONDecodeError)'})

    def _handle_execute_errors(self, url, data, captcha_sid, captcha_key, resp):
        error_code = resp['execute_errors'][0]['error_code']
        if error_code == 29:
            mark_account_rate_limited(self.account)
            self.account = load_account()
            data['access_token'] = self.account.token
            return self._get_api_response(url, data, captcha_sid, captcha_key)
        else:
            return resp['response']

    def _handle_requests_error(self, url, data, captcha_sid, captcha_key):
        if self.n_try < 10:
            release_account(self.account)
            release_proxy(self.proxy)
            self.account = load_account()
            self.proxy = load_proxy()
            sleep(uniform(3, 10))
            self.n_try += 1
            return self._get_api_response(url, data, captcha_sid, captcha_key)
        else:
            self.errors.append({'error_msg': 'VK API request max retries error'})

    def _handle_api_error(self, captcha_key, captcha_sid, data, resp, url):

        if resp['error']['error_msg'] == 'Captcha needed':
            captcha_sid = resp['error']['captcha_sid']
            captcha_img = resp['error']['captcha_img']
            captcha_key = anticaptcha(captcha_img, RUCAPTCHA_KEY)
            if captcha_key:
                return self._get_api_response(url, data, captcha_sid, captcha_key)
            else:
                self.errors.append(resp['error'])
                return None

        elif resp['error']['error_code'] in API_SLEEPING_ERRORS:
            sleep(uniform(120, 180))
            return self._get_api_response(url, data, captcha_sid, captcha_key)

        elif resp['error']['error_code'] in TOKEN_FATAL_ERRORS:
            mark_account_dead(self.account)
            self.account = load_account()
            data['access_token'] = self.account.token
            return self._get_api_response(url, data, captcha_sid, captcha_key)

        elif resp['error']['error_code'] in TOKEN_SLEEPING_ERRORS:
            mark_account_rate_limited(self.account)
            self.account = load_account()
            data['access_token'] = self.account.token
            return self._get_api_response(url, data, captcha_sid, captcha_key)

        else:
            self.errors.append(resp['error'])
            return None

    def _api_response(self, method, params=None):
        """
        Возвращает ответ от API ВК (None - если ошибка)

        :param method:  str, название метода API ВК
        :param params:  dict, параметры метода
        :return:        dict, разобранный из JSON ответ апи ВК (None - если ошибка)
        """
        url = f'https://api.vk.com/method/{method}'
        if params:
            params.update({'access_token': self.account.token, 'v': VK_API_VERSION})
        else:
            params = {'access_token': self.account.token, 'v': VK_API_VERSION}
        return self._get_api_response(url=url, data=params)

    def _execute_response(self, code):
        resp = self._api_response('execute', {'code': code})

        if isinstance(resp, int):
            return resp

        if resp is None:
            return None

        execute_falses = [True if x is False else False for x in resp]
        check_falses_methods = [True if x in code else False for x in EXECUTE_FALSES_METHODS]
        if all(execute_falses) and any(check_falses_methods):
            return None
        elif any(execute_falses) and 'audio.add' in code and self.n_try < 3:
            self.n_try += 1
            return self._execute_response(code)
        elif all(execute_falses) and self.n_try < 3:
            mark_account_rate_limited(self.account)
            self.account = load_account()
            self.n_try += 1
            return self._execute_response(code)
        elif all(execute_falses) and self.n_try >= 3:
            return None
        else:
            return resp
