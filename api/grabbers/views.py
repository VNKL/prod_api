from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response

from api.grabbers.serializers import *
from api.grabbers.utils import create_grabber
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
        grabbers = Grabber.objects.filter(owner=request.user)
        serializer = GrabberSerializer(grabbers, many=True)
        return Response(serializer.data)
