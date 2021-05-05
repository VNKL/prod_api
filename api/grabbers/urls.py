from django.urls import path

from .views import *


app_name = 'grabbers'

urlpatterns = [
    path('', GrabbersIndexView.as_view()),
    path('.get', GrabbersGetView.as_view()),
    path('.getAll', GrabbersGetAllView.as_view()),
    path('.add', GrabbersAddView.as_view()),
    path('.downloadCsv', CSVDownloadView.as_view()),
    path('.delete', DeleteGrabberView.as_view()),
]
