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
from .constant import Constant

# mp
from multiprocessing import Process

# Get an instance of a logger
logger = logging.getLogger('web-logger')

class Assisant():
    instance_dict = {}

    def __init__(self, openid):
        self.openid = openid
        self.itchat_ins = itchat.new_instance()
        print("produced a new itchat instance for client(%s)" % openid)
        # storage the itchat instance in a dict
        Assisant.instance_dict[openid] = self

    def get_chatroom(self):
        itchat_ins = self.itchat_ins
        itchat_ins.get_chatrooms(update=True)
        chatrooms = itchat_ins.search_chatrooms(Constant.CHATROOM_NAME)
        if chatrooms:
            return chatrooms[0]
        else:
            r = itchat_ins.create_chatroom(itchat_ins.get_friends()[1:4], topic=Constant.CHATROOM_NAME)
            if r['BaseResponse']['ErrMsg'] == u'请求成功':
                return {'UserName': r['ChatRoomName']}

    def get_friend_status(self, friend):
        ownAccount = self.itchat_ins.get_friends(update=True)[0]
        if friend['UserName'] == ownAccount['UserName']:
            return u'检测到本人账号。'
        elif self.itchat_ins.search_friends(userName=friend['UserName']) is None:
            return u'该用户不在你的好友列表中。'
        else:
            chatroom = self.get_chatroom()
            if chatroom is None:
                return Constant.FAIL_CHATROOM_MSG
            r = self.itchat_ins.add_member_into_chatroom(chatroom['UserName'], [friend])
            if r['BaseResponse']['ErrMsg'] == u'请求成功':
                status = r['MemberList'][0]['MemberStatus']
                self.itchat_ins.delete_member_from_chatroom(chatroom['UserName'], [friend])
                return { 3: u'该好友已经将你加入黑名单。',
                    4: u'该好友已经将你删除。', }.get(status,
                    u'该好友仍旧与你是好友关系。')
            else:
                return u'无法获取好友状态，预计已经达到接口调用限制。'

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
        self.itchat_ins.send(Constant.DEL_REC_DONE_MSG, toUserName='filehelper')

    def check_friend_status(msg):
        chatroomUserName = '@1234567'
        friend = itchat.get_friends()[1]
        r = itchat.add_member_into_chatroom(chatroomUserName, [friend])
        if r['BaseResponse']['ErrMsg'] == '':
            status = r['MemberList'][0]['MemberStatus']
            itchat.delete_member_from_chatroom(chatroom['UserName'], [friend])
            return { 3: u'该好友已经将你加入黑名单。',
                4: u'该好友已经将你删除。', }.get(status,
                u'该好友仍旧与你是好友关系。')

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
        icon = assistant.itchat_ins.get_head_img(userName=user_name)
        friend_list = json.dumps(assistant.itchat_ins.get_friends(update=True))
        group_list = json.dumps(assistant.itchat_ins.get_chatrooms(update=True))
        mp_list = json.dumps(assistant.itchat_ins.get_mps(update=True))

        # add handlers to ithcat instance
        @assistant.itchat_ins.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
        def msg_handler_wapper(msg):
            msg_handler(msg, assistant)
        @assistant.itchat_ins.msg_register([TEXT, RECORDING, PICTURE, NOTE], isGroupChat=True)
        def HandleGroupMsg_wapper(msg):
            HandleGroupMsg(msg, assistant)
        @assistant.itchat_ins.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE], isMpChat=True)
        def mp_msg_handler_wapper(msg):
            mp_msg_handler(msg, assistant)

        print("login info: uin=%s, NickName=%s" % (uin, nick_name));
        print("host=%s" % host)
        new_values = {'openid': assistant.openid, 'uin': uin, 'user_name':user_name, 'nick_name':nick_name, 'online':True,\
                    'webwxuvid':cookies_dict['webwxuvid'], 'webwx_auth_ticket':cookies_dict['webwx_auth_ticket'],\
                    'host':host, 'friend_list':friend_list, 'group_list':group_list, 'mp_list':mp_list, 'icon':icon}
        close_old_connections()
        wc, created = WechatClient.objects.update_or_create(openid=assistant.openid,defaults=new_values,)

        # run itchat instance
        print("run client(openid=%s, uuid:%s)..." % (openid, uuid))
        assistant.itchat_ins.send(Constant.LOGIN_WELCOME_MSG, toUserName='filehelper')
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
        assistant.itchat_ins.send(Constant.LOGOUT_MSG, toUserName='filehelper')
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
