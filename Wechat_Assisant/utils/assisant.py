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

# Django
from django.conf import settings

# mp
from multiprocessing import Process

# Get an instance of a logger
logger = logging.getLogger('web-logger')

class Assisant():
    instance_dict = {}

    def __init__(self, openid):
        self.openid = openid
        self.itchat_ins = itchat.new_instance()
        # storage the itchat instance in a dict
        Assisant.instance_dict[openid] = self

    def del_client_records(self):
        uin = (self.itchat_ins.search_friends())['Uin']
        # delete message
        # close_old_connections()
        # msg_records = Message.objects.filter(msg_uin=uin)
        # for msg in msg_records.iterator():
        #     msg.delete()
        # delete notification message
        close_old_connections()
        notify_msg_records = NotifyMessage.objects.filter(uin=uin)
        for msg in notify_msg_records.iterator():
            msg.delete()
        self.itchat_ins.send(settings.DEL_REC_DONE_MSG, toUserName='filehelper')

    @staticmethod
    def get_QRuuid(openid):
        assistant = Assisant.get_assistant(openid)
        uuid = assistant.itchat_ins.get_QRuuid()
        return uuid

    @staticmethod
    def run_assisant(uuid, openid):
        assistant = Assisant.get_assistant(openid)

        # init or update client records
        session, host = assistant.itchat_ins.set_login(openid, exitCallback=Assisant.turn_offline)
        cookies_dict = session.cookies.get_dict()
        uin = (assistant.itchat_ins.search_friends())['Uin']
        user_name = (assistant.itchat_ins.search_friends())['UserName']
        nick_name = (assistant.itchat_ins.search_friends())['NickName']

        # add handlers to ithcat instance
        @assistant.itchat_ins.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
        def msg_handler_wapper(msg):
            msg_handler(msg, assistant)
        @assistant.itchat_ins.msg_register([TEXT, RECORDING, PICTURE, NOTE], isGroupChat=True)
        def HandleGroupMsg_wapper(msg):
            HandleGroupMsg(msg, assistant)

        print("login info: uin=%s, NickName=%s" % (uin, nick_name));
        print("host=%s" % host)
        new_values = {'openid': assistant.openid, 'uin': uin, 'user_name':user_name, 'nick_name':nick_name, 'online':True,\
                    'webwxuvid':cookies_dict['webwxuvid'], 'webwx_auth_ticket':cookies_dict['webwx_auth_ticket'],\
                    'host':host}
        close_old_connections()
        wc, created = WechatClient.objects.update_or_create(openid=assistant.openid,defaults=new_values,)

        # run itchat instance
        print("run client(openid=%s, uuid:%s)..." % (openid, uuid))
        assistant.itchat_ins.send(settings.LOGIN_WELCOME_MSG, toUserName='filehelper')
        assistant.itchat_ins.run()

    @staticmethod
    def check_login(uuid, openid):
        assistant = Assisant.get_assistant(openid)
        print('check login status for uuid = %s' % uuid)
        isLoggedIn = False
        wc = get_wc(openid=openid)
        while not isLoggedIn:
            status = assistant.itchat_ins.check_login(uuid)
            if status == '200':
                isLoggedIn = True
                wc.login_status = 200
                wc.save()
            elif status == '201':
                if isLoggedIn is not None:
                    print('(uuid=%s)Please press confirm on your phone.' % uuid)
                    isLoggedIn = None
                    wc.login_status = 201
                    wc.save()
            else:
                print('(uuid=%s)QR code Time out.' % uuid)
                wc.login_status = 408
                wc.save()
                break
        if isLoggedIn:
            return True
        return False

    @staticmethod
    def login_returned_client(wc, openid):
        assistant = Assisant.get_assistant(openid)
        uuid = assistant.itchat_ins.push_login(wc=wc)
        return uuid

    @staticmethod
    def run_returned_client(openid, uuid):
        print("check login status of client(uuid:%s)" % uuid)
        logined = Assisant.check_login(uuid, openid)
        if logined:
            print("client(uuid:%s, openid:%s) logined! run..." % (uuid, openid))
            Assisant.run_assisant(uuid, openid)

    # call back fuction
    # provoked when a user log out
    # turn his/her on-line status to off-line
    @staticmethod
    def turn_offline(openid):
        assistant = Assisant.get_assistant(openid)
        uin = (assistant.itchat_ins.search_friends())['Uin']
        assistant.itchat_ins.send(settings.LOGOUT_MSG, toUserName='filehelper')
        print("client(openid=%s, uin=%s) turned off" % (openid, uin))
        Assisant.instance_dict.pop(openid, None)
        wc = get_wc(uin=uin)
        if wc:
            wc.online = False
            wc.save()
            print("[turn_offline] client(uid=%s) turn offline successfully" % (wc.uin))
            return True
        return False

    @staticmethod
    def get_assistant(openid):
        if openid in Assisant.instance_dict:
            return Assisant.instance_dict[openid]
        else:
            assistant = Assisant(openid)
            return assistant
