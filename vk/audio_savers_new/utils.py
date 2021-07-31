from python_rucaptcha import ImageCaptcha

from api.settings import RUCAPTCHA_KEY


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

    if len(offset_batches[-1]) < len(offset_batches[-2]):
        offset_batches[-2].extend(offset_batches[-1])
        offset_batches.pop(-1)

    min_max_offsets = []
    for x in offset_batches:
        min_max_offsets.append({'min': min(x), 'max': max(x)})

    return min_max_offsets
