from django.conf.urls import url
from werobot.contrib.django import make_view
from .utils.mp_handler import mp_robot

from . import views

urlpatterns = [
    url(r'^(?i)index', views.index, name='index'),
    url(r'^(?i)pushlogin', views.pushlogin, name='pushlogin'),
    url(r'^(?i)wxmp', make_view(mp_robot), name='mp_robot'),
]
