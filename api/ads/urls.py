from django.urls import path

from .views import *


app_name = 'ads'

urlpatterns = [
    path('', AdsIndexView.as_view()),
    path('.getCampaign', GetCampaignView.as_view()),
    path('.getAllCampaigns', GetAllCampaigns.as_view()),
    path('.createCampaign', CreateCampaignView.as_view()),
    path('.renameCampaign', RenameCampaignView.as_view()),
    path('.deleteCampaign', DeleteCampaignView.as_view()),
    path('.updateCampaignStats', UpdateCampaignStatsView.as_view()),
    path('.updateSegmentSizes', UpdateSegmentSizesView.as_view()),
    path('.getAutomate', GetAutomateView.as_view()),
    path('.getAllAutomates', GetAllAutomates.as_view()),
    path('.createAutomate', CreateAutomateView.as_view()),
    path('.stopAutomate', StopAutomateView.as_view()),
    path('.getCabinetsAndGroups', GetCabinetsAndGroupsView.as_view()),
    path('.getRetarget', GetRetargetView.as_view()),
    path('.downloadCampaignStats', DownloadCampaignStatsView.as_view())
]
