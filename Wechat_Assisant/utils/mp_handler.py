# -*- coding:utf8 -*-
import re
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
    greet = "Hi, nice to meet you! Why don't you input 'login' to enjoy our service? :)"
    help_menue = \
    """
    Oh, I bet you feel confused now. Actually, only one thing you need to do currently:
    Input 'login'
    """

    @robot.subscribe
    def subscribe(message):
        return 'Hello My Friend!'

    @mp_robot.text
    def text_reply(message):
        if re.match('login', message.content, re.IGNORECASE):
            push_res = mp_pushlogin(message)
            if push_res:
                rely_text = 'please wait and comfirm login on you phone'
                return rely_text
            else:
                return mp_login(messages)
        else:
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
        return push(from_openid)

    return mp_robot

mp_robot = run_mp()
