from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from .serializers import *
from .models import User
from .utils import bind_vk, unbind_vk


class UserIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'error': 'Use users methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class UserGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        if request.query_params.get('extended'):
            serializer = UserExtendedSerializer(user, context={'request': request})
        else:
            serializer = UserSerializer(user)
        return Response(serializer.data)


class UserCreateView(CreateAPIView):
    model = User
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAdminUser]


class UserBindVkView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.query_params.get('code')
        username = request.query_params.get('state')
        if code:
            bind_vk(code, username)

        return HttpResponseRedirect(redirect_to='http://from-shame-to-fame.ru/')


class UserUnbindVkView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        unbind_vk(user)
        serializer = UserSerializer(user)
        return Response(serializer.data)
