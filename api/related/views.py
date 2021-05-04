from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response
from urllib.parse import quote

from api.related.serializers import *
from api.related.utils import create_scanner, related_results_to_csv_filename, related_results_to_filebody, \
    delete_scanner
from api.users.models import User
from api.users.permissions import RelatedPermission


from multiprocessing import Process


class RelatedIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        return Response({'error': 'Use related methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class RelatedAddView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = CreateScannerSerializer(data=request.query_params)
        if serializer.is_valid():
            scanner = create_scanner(user=user, data=serializer.validated_data)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_scanner',), kwargs=scanner)
            process.start()
            return Response(scanner)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RelatedGetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        serializer = GetScannerSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            scanner = get_object_or_404(Scanner, pk=serializer.validated_data['id'], owner=user)
            if serializer.validated_data['extended']:
                scanner = ScannerExtendedSerializer(scanner)
            else:
                scanner = ScannerSerializer(scanner)
            return Response(scanner.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RelatedGetAllView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        scanners = Scanner.objects.filter(owner=request.user).order_by('-pk')
        serializer = ScannerSerializer(scanners, many=True)
        return Response(serializer.data)


class CSVDownloadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        serializer = GetScannerSerializer(data=request.query_params)
        if serializer.is_valid():
            scanner = Scanner.objects.filter(owner__username=request.user.username,
                                             pk=serializer.validated_data['id']).first()
            if scanner:
                scanner = ScannerExtendedSerializer(scanner).data
                filename = quote(related_results_to_csv_filename(scanner))
                filebody = related_results_to_filebody(scanner)
                response = HttpResponse(filebody, content_type='text/csv', charset='utf-16')
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteRelatedView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, RelatedPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = GetScannerSerializer(data=request.query_params)
        if serializer.is_valid():
            result = delete_scanner(user=user, data=serializer.validated_data)
            if list(result.keys())[0] == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
