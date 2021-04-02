from django.urls import path

from .views import *


app_name = 'charts'

urlpatterns = [
    path('', ChartsIndexView.as_view()),
    path('.get', ChartsGetView.as_view()),
    path('.getAll', ChartsGetAllView.as_view()),
    path('.add', ChartsAddView.as_view()),
    path('.addAll', ChartsAddAllView.as_view()),
    path('.addPeriod', ChartsAddPeriodView.as_view()),
    path('.addAllPeriod', ChartsAddAllPeriodView.as_view()),
    path('.search', ChartsSearchView.as_view()),
    path('.getTopDays', ChartsGetTopDaysView.as_view()),
    path('.getTopDeltas', ChartsGetTopDeltasView.as_view()),
    path('.getStats', ChartsGetStatsView.as_view()),
    path('.delDuplicates', ChartsDelDuplicatesView.as_view()),
    path('.getTrack', ChartsGetTrackView.as_view()),
]
