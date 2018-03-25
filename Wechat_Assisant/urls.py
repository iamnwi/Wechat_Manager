from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?i)index', views.index, name='index'),
    # url(r'^(?i)login', views.login, name='login'),
]
