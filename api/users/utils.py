import requests

from api.users.models import User
from api.settings import VK_APP_ID, VK_APP_SECRET


def bind_vk(code, django_username):
    url = f'https://oauth.vk.com/access_token?client_id={VK_APP_ID}' \
                                            f'&client_secret={VK_APP_SECRET}' \
                                            f'&redirect_uri=http://77.223.106.195:70/api/users.bindVk' \
                                            f'&code={code}'
    resp = requests.get(url).json()
    print(resp)
    if 'access_token' in resp.keys():
        user_data = {
            'token': resp['access_token'],
            'user_id': resp['user_id'],
            'django_username': django_username,
            'ava_url': get_ava_url_from_vk(resp['access_token'])
        }
        update_user_object(user_data)


def unbind_vk(user):
    if user:
        user.has_token = False
        user.save()


def get_ava_url_from_vk(token):
    url = f'https://api.vk.com/method/users.get?fields=photo_200&access_token={token}&v=5.96'
    resp = requests.get(url).json()
    if 'response' in resp.keys():
        return resp['response'][0]['photo_200']


def update_user_object(user_data):
    user = User.objects.filter(username=user_data['django_username']).first()
    if user:
        user.ads_token = user_data['token']
        user.user_id = user_data['user_id']
        user.ava_url = user_data['ava_url']
        user.has_token = True
        user.save()
    else:
        print('err')
