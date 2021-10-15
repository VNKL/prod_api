from urllib.parse import quote

from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django import db
from rest_framework import views, status
from rest_framework import permissions
from rest_framework.response import Response

from api.ads.serializers import *
from api.ads.utils import create_campaign, create_automate, update_campaign_stats, get_cabs_and_groups, get_retarget, \
    stop_automate, camp_stat_to_filename, camp_stat_to_str, delete_campaign, rename_campaign
from api.users.models import User
from api.users.permissions import AdsPermission

from multiprocessing import Process


class AdsIndexView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        return Response({'error': 'Use ads methods'},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)


class CreateCampaignView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = CreateCampaignSerializer(data=request.query_params)
        if serializer.is_valid():
            campaign = create_campaign(user=user, data=serializer.validated_data)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_campaign',), kwargs=campaign)
            process.start()
            return Response(campaign)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetCampaignView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            campaign = get_object_or_404(Campaign, campaign_id=serializer.validated_data['id'], owner=user)
            if serializer.validated_data['extended']:
                campaign = CampaignExtendedSerializer(campaign)
            else:
                campaign = CampaignSerializer(campaign)
            return Response(campaign.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RenameCampaignView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = RenameCampaignSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            campaign = get_object_or_404(Campaign, campaign_id=serializer.validated_data['id'], owner=user)
            campaign = rename_campaign(campaign=campaign, title=serializer.validated_data['title'])
            campaign = CampaignExtendedSerializer(campaign)
            return Response(campaign.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCampaignView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            result = delete_campaign(user=user, data=serializer.validated_data)
            if list(result.keys())[0] == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAllCampaigns(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        campaigns = Campaign.objects.filter(owner=request.user).order_by('-create_date')
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data)


class UpdateCampaignStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            campaign = get_object_or_404(Campaign, campaign_id=serializer.validated_data['id'], owner=user)
            campaign, _ = update_campaign_stats(campaign)
            if serializer.validated_data['extended']:
                campaign = CampaignExtendedSerializer(campaign)
            else:
                campaign = CampaignSerializer(campaign)
            return Response(campaign.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateSegmentSizesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            campaign = Campaign.objects.filter(campaign_id=serializer.validated_data['id'], owner=user).first()
            if campaign:
                db.connections.close_all()
                process = Process(target=call_command, args=('update_segment_sizes',),
                                  kwargs={'campaign_id': campaign.campaign_id})
                process.start()
                return Response({'response': 'update campaign segments sizes is starting'})
            else:
                return Response({'error': 'Campaign not found'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAutomateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            user = get_object_or_404(User, username=request.user.username)
            automate = get_object_or_404(Automate, pk=serializer.validated_data['id'], campaign__owner=user)
            if serializer.validated_data['extended']:
                automate = AutomateExtendedSerializer(automate)
            else:
                automate = AutomateSerializer(automate)
            return Response(automate.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAllAutomates(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        automates = Automate.objects.filter(campaign__owner=request.user)
        serializer = AutomateSerializer(automates, many=True)
        return Response(serializer.data)


class CreateAutomateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = CreateAutomateSerializer(data=request.query_params)
        if serializer.is_valid():
            automate = create_automate(user=user, data=serializer.validated_data)
            if list(automate.keys())[0] == 'error':
                return Response(automate, status=status.HTTP_400_BAD_REQUEST)
            db.connections.close_all()
            process = Process(target=call_command, args=('start_automate',), kwargs=automate)
            process.start()
            return Response(automate)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StopAutomateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        user = get_object_or_404(User, username=request.user.username)
        serializer = StopAutomateSerializer(data=request.query_params)
        if serializer.is_valid():
            result = stop_automate(user=user, data=serializer.validated_data)
            if list(result.keys())[0] == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetCabinetsAndGroupsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        result = get_cabs_and_groups(request.user.username)
        if 'error' not in result.keys():
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class GetRetargetView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetRetargetSerializer(data=request.query_params)
        if serializer.is_valid():
            retarget = get_retarget(request.user.username, serializer.validated_data)
            if isinstance(retarget, list):
                return Response(retarget, status=status.HTTP_200_OK)
            elif isinstance(retarget, dict):
                return Response(retarget, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': 'error with get retarget'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DownloadCampaignStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, AdsPermission]

    def get(self, request):
        serializer = GetSerializer(data=request.query_params)
        if serializer.is_valid():
            camp = Campaign.objects.filter(owner__username=request.user.username,
                                           campaign_id=serializer.validated_data['id']).first()
            if camp:
                camp = CampaignExtendedSerializer(camp).data
                filename = quote(camp_stat_to_filename(camp))
                filebody = camp_stat_to_str(camp)
                response = HttpResponse(filebody, content_type='text/csv', charset='utf-16')
                response['Content-Disposition'] = "attachment; filename=%s" % filename
                return response

            else:
                return Response({'error': 'not found or no permissions'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
