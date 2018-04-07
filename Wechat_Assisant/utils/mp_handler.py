# -*- coding:utf8 -*-
from werobot import WeRoBot

from django.conf import settings
from .wechatmputils import *
from ..views import push
from .bitly import *
from Wechat_Assisant.models import ShortUrl
# mp
from multiprocessing import Process

def run_mp():
    # mp = init_mp()
    # p = Process(target=refresh_access_token, args=(mp, ))
    # p.daemon = True
    # p.start()
    # access_token = get_access_token(settings.MP_APP_ID)
    mp_robot = WeRoBot(token=settings.MP_TOKEN)
    mp_robot.config["APP_ID"] = settings.MP_APP_ID
    mp_robot.config["APP_SECRET"] = settings.MP_APP_SECRET

    @mp_robot.handler
    def text_reply(message):
        if message.content == "login":
            return mp_login(message)
        elif message.content == "quick-login":
            return mp_pushlogin(message)
        elif message.content == "logout":
            from_openid = message.source
            return ("openid %s inputed a logout command" % from_openid)
        else:
            help_menue = \
            """
            Hi, here are the commands I know:
            login: scan QR code on a website and start our services
            quick-login: a convenient login without scaning QR code(available after login)
            logout: end our services
            """
            return help_menue

    def mp_login(message):
        from_openid = message.source
        # otain short url from existed records or create a new record
        qs = ShortUrl.objects.filter(openid=from_openid)
        if qs.exists():
            s_url = qs.get(openid=openid).login_url
        else:
            url = 'http://60.205.223.152/Wechat_Assisant/index?openid=%s' % from_openid
            s_url = shorten(url)
            obj = ShortUrl(openid=from_openid, login_url=s_url)
            obj.save()
        # create reply msg
        rely_text = 'please use another device to browse the webpage %s to finish login' % s_url
        return rely_text

    def mp_pushlogin(message):
        from_openid = message.source
        push(from_openid)
        rely_text = 'please wait and comfirm login on you phone'
        return rely_text

    return mp_robot

mp_robot = run_mp()
