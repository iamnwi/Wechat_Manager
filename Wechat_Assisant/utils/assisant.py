# -*- coding:utf8 -*-
import re
import sys
import time
import os
import shutil
import requests
import json
import logging

# my itchat
from .site_package import itchat
from .site_package.itchat.content import *
from .assisantutils import *
from Wechat_Assisant.models import *

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Assisant():
    def __init__(self, openid):
        self.uuid = None
        self.openid = openid

    def init_client(self):
        session, host = itchat.set_login(exitCallback=turn_offline)
        cookies_dict = session.cookies.get_dict()
        uin = (itchat.search_friends())['Uin']
        user_name = (itchat.search_friends())['UserName']
        nick_name = (itchat.search_friends())['NickName']
        logger.info("login info: uin=%s, NickName=%s" % (uin, nick_name));
        logger.info("host=%s" % host)
        wc = get_wc(openid=self.openid)
        if wc:
            wc.user_name = user_name
            wc.nick_name = nick_name
            wc.online = True
            wc.save()
        else:
            logger.info("openid=%s, first login, cookies=%s" % (self.openid, cookies_dict))
            wc = WechatClient(openid=self.openid, uin=uin, user_name=user_name, nick_name=nick_name, online=True, \
                            webwxuvid=cookies_dict['webwxuvid'], webwx_auth_ticket=cookies_dict['webwx_auth_ticket'], \
                            host=host)
            wc.save()

    def run(self):
        self.init_client()
        itchat.run()

    def get_QRuuid(self):
        self.uuid = itchat.get_QRuuid()
        return self.uuid

    def check_login(self):
        isLoggedIn = False
        while not isLoggedIn:
            status = itchat.check_login(self.uuid)
            if status == '200':
                isLoggedIn = True
            elif status == '201':
                if isLoggedIn is not None:
                    logger.info('(uuid:%s)Please press confirm on your phone.' % self.uuid)
                    isLoggedIn = None
            else:
                break
        if isLoggedIn:
            return True
        else:
            logger.info('(uuid:%s)Log in time out, reloading QR code.' % self.uuid)
            return False

    def login_returned_client(self, wc):
        self.uuid = itchat.push_login(wc=wc)
        return self.uuid
