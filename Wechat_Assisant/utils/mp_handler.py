# -*- coding:utf8 -*-
import re
import requests
from werobot import WeRoBot

from django.conf import settings
from .wechatmputils import *
from ..views import push, kick
from Wechat_Assisant.models import *
from .constant import Constant

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

    @mp_robot.subscribe
    def subscribe(message):
        return Constant.MP_GREET

    @mp_robot.text
    def text_reply(message):
        if re.match('login', message.content, re.IGNORECASE):
            push_res = mp_pushlogin(message)
            if push_res:
                rely_text = Constant.MP_COMFIRM_LOGIN
                return rely_text
            else:
                return mp_login(message)
        elif re.match('function', message.content, re.IGNORECASE):
            return Constant.MP_FUNCTION
        elif re.match('how', message.content, re.IGNORECASE):
            return Constant.MP_HOW_LOGIN
        elif re.match('kick', message.content, re.IGNORECASE) \
                and message.source == Constant.ADMIN_OPENID:
            mp_kick()
            return "Done"
        else:
            return Constant.MP_HELP

    def mp_login(message):
        # otain short url from existed records or create a new record
        from_openid = message.source
        close_old_connections()
        url, created = ShortUrl.objects.get_or_create(openid=from_openid)
        sid = url.id + 10000
        s_url = 'http://%s/wm/%s' % (settings.WECHAT_MANAGER_SERVER, sid)
        # create reply msg
        rely_text = "%s\n%s" % (Constant.MP_LOGIN_VIA_LINK, s_url)
        return rely_text

    def mp_pushlogin(message):
        from_openid = message.source
        return push(from_openid)

    def mp_kick():
        kick()

    return mp_robot

mp_robot = run_mp()
