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
