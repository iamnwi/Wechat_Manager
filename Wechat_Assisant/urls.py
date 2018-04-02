from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?i)index', views.index, name='index'),
    url(r'^(?i)mp', views.mp, name='mp'),
]
