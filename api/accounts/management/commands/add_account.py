import vk_api

from django.core.management.base import BaseCommand
from django import db
from random import randint

from api.accounts.models import Account
from api.accounts.serializers import AccountSerializer
from vk.users_audios.parser import captcha_handler


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
        db.connections.close_all()
        return acc_serializer.data

    new_password = random_password()
    vk = vk_api.VkApi(login=login, password=password, app_id=6121396, api_version='5.116', scope=1073737727,
                      captcha_handler=captcha_handler)

    try:
        vk.auth()
        api = vk.get_api()
        token_resp = api.account.changePassword(old_password=password, new_password=new_password)
        if isinstance(token_resp, dict) and 'token' in token_resp.keys():
            token = token_resp['token']
            vk.token = {'access_token': token}
            user_resp = api.users.get()
            if isinstance(user_resp, list) and len(user_resp) > 0:
                user = user_resp[0]
                if isinstance(user, dict) and 'id' in user.keys():
                    user_id = user['id']
                    return save_account(login, new_password, token, user_id)

    except (Exception, vk_api.AuthError, vk_api.exceptions.ApiError, vk_api.exceptions.Captcha):
        return save_account(None, None, None, None)


def save_account(login, password, token, user_id):
    if not token and not user_id:
        return None

    account = Account(login=login,
                      password=password,
                      token=token,
                      user_id=user_id)
    account.save()
    db.connections.close_all()
    return {
        'login': login,
        'password': password,
        'token': token,
        'user_id': user_id
    }


def random_password():
    simbols = 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890'
    password = ''
    for i in range(30):
        s = randint(0, len(simbols) - 1)
        password += simbols[s]
    return password
