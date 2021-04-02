from django.urls import path

from .views import *


app_name = 'related'

urlpatterns = [
    path('', RelatedIndexView.as_view()),
    path('.get', RelatedGetView.as_view()),
    path('.getAll', RelatedGetAllView.as_view()),
    path('.add', RelatedAddView.as_view()),
]
