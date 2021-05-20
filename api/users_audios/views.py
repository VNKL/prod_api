from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response
from urllib.parse import quote

from api.users_audios.serializers import *
from api.users_audios.utils import *
from api.users.models import User
from api.users.permissions import RelatedPermission


from multiprocessing import Process


class UsersAudiosIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        return Response({'error': 'Use users_audios methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class UsersAudiosAddParserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = CreateParserSerializer(data=request.query_params)
        if serializer.is_valid():
            parser = create_parser(user=user, data=serializer.validated_data)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_users_audios_parser',), kwargs=parser)
            process.start()
            return Response(parser)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersAudiosGetParserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        serializer = GetParserSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            parser = get_object_or_404(Parser, pk=serializer.validated_data['id'], owner=user)
            if serializer.validated_data['extended']:
                parser = ParserExtendedSerializer(parser)
            else:
                parser = ParserSerializer(parser)
            return Response(parser.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UsersAudiosGetAllParsersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        parsers = Parser.objects.filter(owner=request.user).order_by('-pk')
        serializer = ParserSerializer(parsers, many=True)
        return Response(serializer.data)


class CSVDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        serializer = GetParserSerializer(data=request.query_params)
        if serializer.is_valid():
            parser = Parser.objects.filter(owner__username=request.user.username,
                                           pk=serializer.validated_data['id']).first()
            if parser:
                parser = ParserExtendedSerializer(parser).data
                filename = quote(users_audios_results_to_csv_filename(parser))
                filebody = users_audios_results_to_filebody(parser)
                response = HttpResponse(filebody, content_type='text/csv', charset='utf-16')
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteUsersAudiosParserView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = GetParserSerializer(data=request.query_params)
        if serializer.is_valid():
            result = delete_parser(user=user, data=serializer.validated_data)
            if list(result.keys())[0] == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
