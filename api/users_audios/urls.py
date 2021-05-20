from django.urls import path

from .views import *


app_name = 'users_audios'

urlpatterns = [
    path('', UsersAudiosIndexView.as_view()),
    path('.get', UsersAudiosGetParserView.as_view()),
    path('.getAll', UsersAudiosGetAllParsersView.as_view()),
    path('.add', UsersAudiosAddParserView.as_view()),
    path('.downloadCsv', CSVDownloadView.as_view()),
    path('.delete', DeleteUsersAudiosParserView.as_view()),
]
