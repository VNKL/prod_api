from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response
from urllib.parse import quote

from api.grabbers.serializers import *
from api.grabbers.utils import create_grabber, delete_grabber, grabber_results_to_csv_filename, \
    grabber_results_to_filebody
from api.users.models import User
from api.users.permissions import GrabbersPermission


from multiprocessing import Process


class GrabbersIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        return Response({'error': 'Use grabbers methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class GrabbersAddView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = GrabberAddSerializer(data=request.query_params)
        if serializer.is_valid():
            grabber = create_grabber(user=user, data=serializer.validated_data)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_grabber',), kwargs=grabber)
            process.start()
            return Response(grabber)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GrabbersGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        serializer = GrabberGetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            grabber = get_object_or_404(Grabber, pk=serializer.validated_data['id'], owner=user)
            if serializer.validated_data['extended']:
                grabber = GrabberExtendedSerializer(grabber)
            else:
                grabber = GrabberSerializer(grabber)
            return Response(grabber.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GrabbersGetAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        grabbers = Grabber.objects.filter(owner=request.user).order_by('-pk')
        serializer = GrabberSerializer(grabbers, many=True)
        return Response(serializer.data)


class CSVDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        serializer = GrabberGetSerializer(data=request.query_params)
        if serializer.is_valid():
            grabber = Grabber.objects.filter(owner__username=request.user.username,
                                             pk=serializer.validated_data['id']).first()
            if grabber:
                grabber = GrabberExtendedSerializer(grabber).data
                filename = quote(grabber_results_to_csv_filename(grabber))
                filebody = grabber_results_to_filebody(grabber)
                response = HttpResponse(filebody, content_type='text/csv', charset='utf-16')
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteGrabberView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, GrabbersPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = GrabberGetSerializer(data=request.query_params)
        if serializer.is_valid():
            result = delete_grabber(user=user, data=serializer.validated_data)
            if list(result.keys())[0] == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

