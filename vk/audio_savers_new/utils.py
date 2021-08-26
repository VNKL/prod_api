from python_rucaptcha import ImageCaptcha

from api.settings import RUCAPTCHA_KEY


N_MAX_PROCESSES = 80


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
    x = round(max_offset / 6400)
    if 1 <= x <= N_MAX_PROCESSES:
        return x
    elif x < 1:
        return 1
    else:
        return N_MAX_PROCESSES
