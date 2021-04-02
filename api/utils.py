from api.users.models import User
from api.users.serializers import UserSerializer


def my_jwt_response_handler(token, user=None, request=None):
    user = User.objects.get(username=user)
    return {
        'token': token,
        'users': UserSerializer(user, context={'request': request}).data
    }
