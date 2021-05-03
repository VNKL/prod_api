import datetime
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response

from .serializers import *
from api.users.models import User
from api.users.permissions import AnalyzersPermission
from .models import Analyzer
from .utils import create_analyzer


from multiprocessing import Process


class AnalyzerIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AnalyzersPermission]

    def get(self, request):
        return Response({'error': 'Use analyzers methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class AnalyzerAddView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AnalyzersPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = AnalyzerAddSerializer(data=request.query_params)
        if serializer.is_valid():
            analyzer = create_analyzer(user=user, data=serializer.validated_data)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_analyzer',), kwargs=analyzer)
            process.start()
            return Response(analyzer)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnalyzerGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AnalyzersPermission]

    def get(self, request):
        serializer = AnalyzerGetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            analyzer = get_object_or_404(Analyzer, pk=serializer.validated_data['id'], owner=user)
            if isinstance(analyzer.result, str):
                analyzer.result = eval(analyzer.result)
            if serializer.validated_data['extended']:
                analyzer = AnalyzerExtendedSerializer(analyzer)
            else:
                analyzer = AnalyzerSerializer(analyzer)
            return Response(analyzer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnalyzerGetAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AnalyzersPermission]

    def get(self, request):
        analyzers = Analyzer.objects.filter(owner=request.user)
        serializer = AnalyzerSerializer(analyzers, many=True)
        return Response(serializer.data)
