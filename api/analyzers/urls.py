from django.urls import path

from .views import *


app_name = 'analyzers'

urlpatterns = [
    path('', AnalyzerIndexView.as_view()),
    path('.add', AnalyzerAddView.as_view()),
    path('.get', AnalyzerGetView.as_view()),
    path('.getAll', AnalyzerGetAllView.as_view()),
]
