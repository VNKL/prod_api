from django.shortcuts import get_object_or_404
from django import db
from rest_framework import viewsets, views, status
from rest_framework import permissions
from rest_framework.response import Response

from api.accounts.serializers import AccountSerializer, AccountAddSerializer, AccountResetSerializer, ProxyAddSerializer, ProxySerializer
from api.accounts.management.commands.add_account import add_account
from api.accounts.management.commands.reset_accounts import reset_one, reset_all
from api.accounts.models import Account, Proxy
from .utils import create_proxy, del_expired_proxy


class AccountIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'detail': 'Use accounts.add, accounts.get or accounts.getAll methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class AccountAddView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        new_acc_serializer = AccountAddSerializer(data=request.query_params)
        if new_acc_serializer.is_valid():
            added_account = add_account(login=new_acc_serializer.validated_data['login'],
                                        password=new_acc_serializer.validated_data['password'])
            if added_account:
                acc_serializer = AccountSerializer(added_account)
                return Response(acc_serializer.data)
            else:
                return Response({'detail': 'Account auth error'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(new_acc_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountGetView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        account = None
        if 'login' in request.query_params.keys():
            account = get_object_or_404(Account, login=request.query_params['login'])
        elif 'user_id' in request.query_params.keys():
            account = get_object_or_404(Account, user_id=request.query_params['user_id'])
        if account:
            acc_serializer = AccountSerializer(account)
            db.connections.close_all()
            return Response(acc_serializer.data)
        else:
            db.connections.close_all()
            return Response({'detail': 'login or user_id are required'}, status=status.HTTP_400_BAD_REQUEST)


class AccountGetAllViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all().order_by('user_id')
    db.connections.close_all()
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAdminUser]


class AccountResetView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        account = None
        settings = AccountResetSerializer(data=request.query_params)
        if settings.is_valid():
            account = reset_one(**settings.validated_data)
        if isinstance(account, dict):
            return Response(account, status=status.HTTP_400_BAD_REQUEST)
        elif account:
            acc_serializer = AccountSerializer(account)
            return Response(acc_serializer.data)
        else:
            return Response({'detail': 'login or user_id are required'}, status=status.HTTP_400_BAD_REQUEST)


class AccountResetAllView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        accounts = None
        settings = AccountResetSerializer(data=request.query_params)
        if settings.is_valid():
            accounts = reset_all(**settings.validated_data)
        if isinstance(accounts, dict):
            return Response(accounts, status=status.HTTP_400_BAD_REQUEST)
        elif accounts:
            acc_serializer = AccountSerializer(accounts, many=True)
            return Response(acc_serializer.data)
        else:
            return Response({'detail': 'No accounts in database'}, status=status.HTTP_400_BAD_REQUEST)


class ProxyAddView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = ProxyAddSerializer(data=request.query_params)
        if serializer.is_valid():
            proxy_obj = create_proxy(proxy=serializer.validated_data['proxy'],
                                     period=serializer.validated_data['period'])
            if proxy_obj:
                prx_serializer = ProxySerializer(proxy_obj)
                return Response(prx_serializer.data)
            else:
                return Response({'detail': 'Proxy parsing error'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProxyDelExpiredView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        response = del_expired_proxy()
        return Response(response, status=status.HTTP_200_OK)


class ProxyGetAllViewSet(viewsets.ModelViewSet):
    queryset = Proxy.objects.all().order_by('-expiration_date')
    db.connections.close_all()
    serializer_class = ProxySerializer
    permission_classes = [permissions.IsAdminUser]
