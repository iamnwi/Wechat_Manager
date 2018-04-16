from django.conf.urls import url
from werobot.contrib.django import make_view
from .utils.mp_handler import mp_robot

from . import views

urlpatterns = [
    url(r'^(?i)index', views.index, name='index'),
    url(r'^(?i)pushlogin', views.pushlogin, name='pushlogin'),
    url(r'^(?i)login$', views.login, name='login'),
    url(r'^(?i)loginstatus$', views.loginstatus, name='loginstatus'),
    url(r'^(?i)wxmp', make_view(mp_robot), name='mp_robot'),
    url(r'^(?i)getuuid$', views.getuuid, name='getuuid'),
    url(r'^(?P<sid>[0-9]+)$', views.extend, name='extend'),
]
