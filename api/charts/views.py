from django.core.management import call_command
from django import db
from rest_framework import views, status, viewsets
from rest_framework import permissions
from rest_framework.response import Response

from .serializers import *
from .utils import *
from api.users.permissions import ChartsPermission

from multiprocessing import Process


class ChartsIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        return Response({'detail': 'Use parsers.add, parsers.get, parsers.getAll, parsers.getAudio or '
                                   'parsers.searchAudio methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class ChartsAddView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings = ChartAddSerializer(data=request.query_params)
        if settings.is_valid():
            chart = add_chart(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsAddAllView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = ChartAddAllSerializer(data=request.query_params)
        if serializer.is_valid():
            db.connections.close_all()
            process = Process(target=call_command, args=('add_all_charts',), kwargs=serializer.validated_data)
            process.start()
            return Response({'parsing charts starts in background'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChartsAddPeriodView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = ChartAddPeriodSerializer(data=request.query_params)
        if serializer.is_valid():
            db.connections.close_all()
            process = Process(target=call_command, args=('add_chart_period',), kwargs=serializer.validated_data)
            process.start()
            return Response({'parsing charts starts in background'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChartsAddAllPeriodView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = ChartAddAllPeriodSerializer(data=request.query_params)
        if serializer.is_valid():
            db.connections.close_all()
            process = Process(target=call_command, args=('add_all_charts_period',), kwargs=serializer.validated_data)
            process.start()
            return Response({'parsing charts starts in background'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChartsGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartGetSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_chart(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsGetAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartGetAllSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_all_charts(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsSearchView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartsSearchSerializer(data=request.query_params)
        if settings.is_valid():
            chart = search(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsGetTopDaysView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartsGetTopSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_top_by_days(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsGetTopDeltasView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartsGetTopSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_top_by_deltas(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsGetStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartGetStatsSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_chart_stats(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)


class ChartsDelDuplicatesView(views.APIView):
    permission_classes = [permissions.IsAdminUser, ChartsPermission]

    def get(self, request):
        db.connections.close_all()
        process = Process(target=call_command, args=('del_duplicates',))
        process.start()
        return Response({'deleting starts in background'}, status=status.HTTP_200_OK)


class ChartsGetTrackView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ChartsPermission]

    def get(self, request):
        settings = ChartsGetTrackSerializer(data=request.query_params)
        if settings.is_valid():
            chart = get_track(**settings.validated_data)
            return Response(chart)
        return Response(settings.errors, status.HTTP_400_BAD_REQUEST)
