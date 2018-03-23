# -*- coding:utf8 -*-
import re
import sys
import time
import os
import shutil
import requests
import json

# my itchat
from site_package import itchat
from site_package.itchat.content import *
from cache import *
from assisantutils import *
from Wechat_Assisant.models import *

class Assisant():
    def __init__(self):
        self.uuid = None

    def init_client(self):
        itchat.set_login(exitCallback=turn_offline)
        uin = (itchat.search_friends())['Uin']
        user_name = (itchat.search_friends())['UserName']
        nick_name = (itchat.search_friends())['NickName']
        print("login info: uin=%s, NickName=%s" % (uin, nick_name));
        client_qs = WechatClient.objects.filter(uin=uin)
        if client_qs.count() == 0:
            wc = WechatClient(uin=uin, user_name=user_name, nick_name=nick_name, online=True)
            wc.save()
        elif client_qs.count() == 1:
            wc = client_qs.get(uin=uin)
            wc.user_name = user_name
            wc.nick_name = nick_name
            wc.online = True
            wc.save()

    def run(self):
        self.init_client()
        itchat.run()

    def get_QRuuid(self):
        print('Getting uuid of QR code.')
        self.uuid = itchat.get_QRuuid()
        return self.uuid

    def check_login(self):
        print('checking login status')
        isLoggedIn = False
        while not isLoggedIn:
            status = itchat.check_login(self.uuid)
            if status == '200':
                isLoggedIn = True
            elif status == '201':
                if isLoggedIn is not None:
                    print('Please press confirm on your phone.')
                    isLoggedIn = None
            else:
                break
        if isLoggedIn:
            return True
        else:
            print('Log in time out, reloading QR code.')
            return False
