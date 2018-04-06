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

# mp
from multiprocessing import Process

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

    @staticmethod
    def get_QRuuid():
        uuid = itchat.get_QRuuid()
        return uuid

    @staticmethod
    def run_assisant(uuid, openid):
        assisant = Assisant(openid)
        assisant.uuid = uuid
        logger.info("client(uuid:%s) logined! run..." % assisant.uuid)
        assisant.run()

    @staticmethod
    def check_login(uuid, openid):
        logger.info('check login status for uuid = %s', uuid)
        isLoggedIn = False
        wc = get_wc(openid=openid)
        while not isLoggedIn:
            status = itchat.check_login(uuid)
            if status == '200':
                isLoggedIn = True
                wc.login_status = 200
                wc.save()
            elif status == '201':
                if isLoggedIn is not None:
                    logger.info('(uuid=%s)Please press confirm on your phone.' % uuid)
                    isLoggedIn = None
                    wc.login_status = 201
                    wc.save()
            else:
                logger.info('(uuid=%s)QR code Time out.' % uuid)
                wc.login_status = 408
                wc.save()
                break
        if isLoggedIn:
            Assisant.run_assisant(uuid, openid)
            return True
        return False

    def login_returned_client(self, wc):
        self.uuid = itchat.push_login(wc=wc)
        return self.uuid
