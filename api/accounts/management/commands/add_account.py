import vk_api

from django.core.management.base import BaseCommand
from random import randint

from vk.auth.auth import VKAuth
from api.accounts.models import Account
from api.accounts.serializers import AccountSerializer


class Command(BaseCommand):
    help = 'change password, get valid token and write Account in database'

    def add_arguments(self, parser):
        parser.add_argument('-login', action='store', dest='login', type=str)
        parser.add_argument('-password', action='store', dest='password', type=str)

    def handle(self, *args, **options):
        login, password = options['login'], options['password']
        add_account(login=login, password=password)


def add_account(login, password):

    account = Account.objects.filter(login=login).first()
    if account and account.is_alive:
        acc_serializer = AccountSerializer(account)
        return acc_serializer.data

    new_password = random_password()
    vk_session = vk_api.VkApi(login, password,)

    try:
        vk_session.auth()
        vk = vk_session.get_api()
        response = vk.account.changePassword(old_password=password, new_password=new_password)
        if response:
            token, user_id = get_token(login=login, password=new_password)
            return save_account(login, new_password, token, user_id)
    except (Exception, vk_api.AuthError, vk_api.exceptions.ApiError, vk_api.exceptions.Captcha):
        token, user_id = get_token(login=login, password=password)
        return save_account(login, password, token, user_id)


def save_account(login, password, token, user_id):
    if not token and not user_id:
        return None

    account = Account(login=login,
                      password=password,
                      token=token,
                      user_id=user_id)
    account.save()
    return {
        'login': login,
        'password': password,
        'token': token,
        'user_id': user_id
    }


def get_token(login, password, proxy=None):
    try:
        vk = VKAuth(['offline,audio,wall,groups,video'], '6146827', '5.116', email=login, pswd=password, proxy=proxy)
        vk.auth()
        return vk.get_token(), vk.get_user_id()
    except ConnectionAbortedError:
        return None, None


def random_password():
    simbols = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890'
    password = ''
    for i in range(30):
        s = randint(0, len(simbols) - 1)
        password += simbols[s]
    return password
