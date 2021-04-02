from django.urls import path
from rest_framework_jwt.views import obtain_jwt_token

from .views import *

app_name = 'users'

urlpatterns = [
    path('', UserIndexView.as_view()),
    path('.auth', obtain_jwt_token),
    path('.create', UserCreateView.as_view()),
    path('.get', UserGetView.as_view()),                         # extended
    path('.bindVk', UserBindVkView.as_view()),
]
