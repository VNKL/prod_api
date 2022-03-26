from django.urls import path

from .views import AccountIndexView, AccountAddView, AccountGetView, AccountGetAllViewSet, \
    AccountResetView, AccountResetAllView, ProxyAddView, ProxyDelExpiredView, ProxyGetAllViewSet, ProxyResetAllView

app_name = 'accounts'

urlpatterns = [
    path('', AccountIndexView.as_view()),
    path('.add', AccountAddView.as_view()),
    path('.get', AccountGetView.as_view()),
    path('.getAll', AccountGetAllViewSet.as_view({'get': 'list'})),
    path('.reset', AccountResetView.as_view()),
    path('.resetAll', AccountResetAllView.as_view()),
    path('.addProxy', ProxyAddView.as_view()),
    path('.getAllProxies', ProxyGetAllViewSet.as_view({'get': 'list'})),
    path('.delExpiredProxies', ProxyDelExpiredView.as_view()),
    path('.resetAllProxies', ProxyResetAllView.as_view()),
]
