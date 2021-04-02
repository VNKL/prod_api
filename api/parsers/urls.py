from django.urls import path

from .views import ParsersIndexView, ParsersAddView, ParsersGetView,  ParsersGetAllView, \
    ParsersGetAudioView, ParsersSearchAudioView, ParsersDownloadView, CSVDownloadView


app_name = 'parsers'

urlpatterns = [
    path('', ParsersIndexView.as_view()),
    path('.add', ParsersAddView.as_view()),
    path('.get', ParsersGetView.as_view()),
    path('.getAll', ParsersGetAllView.as_view()),
    path('.getAudio', ParsersGetAudioView.as_view()),
    path('.searchAudio', ParsersSearchAudioView.as_view()),
    path('.download', ParsersDownloadView.as_view()),
    path('.downloadCsv', CSVDownloadView.as_view()),
]
