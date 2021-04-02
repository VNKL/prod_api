import mimetypes
import os
from wsgiref.util import FileWrapper
from urllib.parse import quote

from django.core.management import call_command
from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404, get_list_or_404
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response

from api.parsers.serializers import *
from api.users.models import User
from api.users.permissions import ParsersPermission
from .models import Parser
from .utils import create_parser, parsing_results_to_csv_filename, parsing_results_to_filebody


from multiprocessing import Process


class ParsersIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        return Response({'error': 'Use parsers methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ParsersAddView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = ParserAddSerializer(data=request.query_params)
        if serializer.is_valid():
            parser = create_parser(user=user, data=serializer.validated_data)
            process = Process(target=call_command, args=('start_parser',), kwargs=parser)
            process.start()
            return Response(parser)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParsersGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        serializer = ParserGetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            parser = get_object_or_404(Parser, pk=serializer.validated_data['id'], owner=user)
            if serializer.validated_data['extended']:
                parser = ParserExtendedSerializer(parser)
            else:
                parser = ParserSerializer(parser)
            return Response(parser.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParsersGetAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        parsers = Parser.objects.filter(owner=request.user)
        serializer = ParserSerializer(parsers, many=True)
        return Response(serializer.data)


class ParsersGetAudioView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        serializer = AudioGetSerializer(data=request.query_params)
        if serializer.is_valid():
            return self._return_from_valid_serializer(request, serializer)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _return_from_valid_serializer(self, request, serializer):
        audio = self._get_audio(request, serializer)
        if not audio:
            return Response({'detail': "You don't have permissions for this audio"},
                            status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(audio, dict) and 'detail' in audio.keys():
            return Response(audio, status=status.HTTP_400_BAD_REQUEST)
        else:
            audio = AudioSerializer(audio)
        return Response(audio.data)

    @staticmethod
    def _get_audio(request, serializer):
        user = get_object_or_404(User, username=request.user.username)
        audio = get_object_or_404(Audio, owner_id=serializer.validated_data['owner_id'],
                                  audio_id=serializer.validated_data['audio_id'])
        if audio:
            audios_parsers = audio.parsers
            check = [True if x.owner == user else False for x in audios_parsers.all()]
            if any(check):
                return audio

        return {'detail': "Not found"}


class ParsersSearchAudioView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        serializer = AudioSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            search_params = {'artist': serializer.validated_data['artist'],
                             'title': serializer.validated_data['title']}
            if serializer.validated_data['has_savers']:
                search_params['has_savers'] = True
            audios = get_list_or_404(Audio.objects.order_by('-savers_count'), **search_params)
            audios = AudioSerializer(audios, many=True)
            return Response(audios.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParsersDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        serializer = ParserDownloadSerializer(data=request.query_params)
        if serializer.is_valid():
            parser = Parser.objects.filter(owner__username=request.user.username,
                                           pk=serializer.validated_data['id']).first()
            if parser:
                path = parser.result_path
                filename = quote(path.split('/')[-1])
                chunk_size = 8192
                response = StreamingHttpResponse(FileWrapper(open(path, 'rb'), chunk_size),
                                                 content_type=mimetypes.guess_type(path)[0])
                response['Content-Length'] = os.path.getsize(path)
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CSVDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ParsersPermission]

    def get(self, request):
        serializer = ParserGetSerializer(data=request.query_params)
        if serializer.is_valid():
            parser = Parser.objects.filter(owner__username=request.user.username,
                                           pk=serializer.validated_data['id']).first()
            if parser:
                parser = ParserExtendedSerializer(parser).data
                filename = quote(parsing_results_to_csv_filename(parser))
                filebody = parsing_results_to_filebody(parser)
                response = HttpResponse(filebody, content_type='text/csv', charset='utf-16')
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
