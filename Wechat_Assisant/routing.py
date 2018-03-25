from django.conf.urls import url

from . import consumer

websocket_urlpatterns = [
    url(r'^wslogin$', consumer.WechatConsumer),
]
