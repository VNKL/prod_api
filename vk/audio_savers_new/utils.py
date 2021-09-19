from python_rucaptcha import ImageCaptcha
from django import db

from api.settings import RUCAPTCHA_KEY
from api.accounts.models import ParsingThreadCount


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


def captcha_handler(captcha):
    captcha_img = captcha.get_url()
    captcha_key = anticaptcha(captcha_img, RUCAPTCHA_KEY)
    return captcha.try_again(captcha_key)


def get_offset_batches(max_offset, n_batches=8):
    offset_list = list(range(50, max_offset + 50, 50))
    delimiter = int(len(offset_list) / n_batches)
    offset_batches = []
    for x in range(0, len(offset_list), delimiter):
        y = x + delimiter
        offset_batches.append(offset_list[x:y])

    if len(offset_batches) > 2 and len(offset_batches[-1]) < len(offset_batches[-2]):
        offset_batches[-2].extend(offset_batches[-1])
        offset_batches.pop(-1)

    min_max_offsets = []
    for x in offset_batches:
        min_max_offsets.append({'min': min(x), 'max': max(x)})

    return min_max_offsets


def convert_users_domains_to_execute_batches(domains):
    unique_domains = list(set(domains))
    domains_count = len(unique_domains)
    by_1000_items = []
    for x in range(0, domains_count, 1000):
        y = x + 1000 if x + 1000 <= domains_count + 1 else None
        by_1000_items.append(unique_domains[x:y])

    if len(by_1000_items[-1]) == 0:
        by_1000_items.pop(-1)

    batches_per_request = 7
    by_1000_count = len(by_1000_items)
    for_execute_batches = []
    for x in range(0, by_1000_count, batches_per_request):
        y = x + batches_per_request if x + batches_per_request <= by_1000_count else None
        for_execute_batches.append(by_1000_items[x:y])

    return for_execute_batches


def code_for_get_users(batch):
    code = 'return ['
    for domains in batch:
        code += 'API.users.get({fields: "domain", user_ids: "' + ','.join(domains) + '"}), '
    code = code[:-2]
    code += '];'
    return code


def unpack_execute_get_users(resp):
    users_dict = {}
    for pack in resp:
        for user in pack:
            users_dict[user['domain']] = user['id']
    return users_dict


def calculate_n_threads(max_offset):
    try:
        db.connections.close_all()
        threads_obj = ParsingThreadCount.objects.filter().first()
        max_threads = threads_obj.max_threads
        offset_param = threads_obj.offset_param
        db.connections.close_all()
    except Exception as err_msg:
        print('!!! error in calculate_n_threads', err_msg)
        max_threads = 64
        offset_param = 6400

    x = round(max_offset / offset_param)
    if 1 <= x <= max_threads:
        return x
    elif x < 1:
        return 1
    else:
        return max_threads


def calculate_n_threads_new(pairs):
    try:
        db.connections.close_all()
        threads_obj = ParsingThreadCount.objects.filter().first()
        max_threads = threads_obj.max_threads
        offset_param = threads_obj.offset_param
        db.connections.close_all()
    except Exception as err_msg:
        print('!!! error in calculate_n_threads', err_msg)
        max_threads = 64
        offset_param = 6400

    x = round(len(pairs) / (offset_param / 50))
    if 1 <= x <= max_threads:
        return x
    elif x < 1:
        return 1
    else:
        return max_threads


def slice_audios_to_id_offset_pairs(audios):
    id_offset_pairs = []
    audio_ids = []
    for audio in audios:
        audio_id = f"{audio['owner_id']}_{audio['audio_id']}"
        audio_ids.append(audio_id)
        savers_count = audio['savers_count']
        for offset in range(0, savers_count, 50):
            id_offset_pairs.append({'audio_id': audio_id, 'offset': offset})

    return id_offset_pairs, audio_ids


def slice_to_batches(array, n_threads):
    batches = []
    len_pairs = len(array)
    d = round(len_pairs / n_threads)
    for n, x in enumerate(range(0, len_pairs, d)):
        if n + 1 == n_threads:
            y = None
            batches.append(array[x:y])
            break
        else:
            y = x + d if x + d <= len_pairs else None
            batches.append(array[x:y])

    return batches


def result_list_to_dict(result_list):
    result_dict = {}
    for pack in result_list:
        audio_id = list(pack.keys())[0]
        if audio_id in result_dict.keys():
            result_dict[audio_id].extend(pack[audio_id])
        else:
            result_dict[audio_id] = pack[audio_id]

    return result_dict


def calculate_n_threads_for_savers_count(audio_ids):
    try:
        db.connections.close_all()
        threads_obj = ParsingThreadCount.objects.filter().first()
        max_threads = threads_obj.savers_count_max_threads
        division_param = threads_obj.savers_count_param
        db.connections.close_all()
    except Exception as err_msg:
        print('!!! error in calculate_n_threads_for_savers_count:', err_msg)
        max_threads = 8
        division_param = 25

    count = len(audio_ids)
    x = round(count / division_param)
    if 1 <= x <= max_threads:
        return x
    elif x < 1:
        return 1
    else:
        return max_threads

