# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class WechatClient(models.Model):
    openid = models.CharField(max_length=200, default='None')
    uin = models.CharField(max_length=200)
    user_name = models.CharField(max_length=200)
    nick_name = models.CharField(max_length=200)
    online = models.BooleanField(default=False)
    # login status
    # 0: initial status, 200: logined, 201: wait for scan, 408: qrcode timeout
    login_status = models.IntegerField(blank=False, default='0')
    # cookies for push login
    host = models.CharField(max_length=50, default='None')
    webwxuvid = models.CharField(max_length=100, default='None')
    webwx_auth_ticket = models.CharField(max_length=190, default='None')

    def __str__(self):
        return ("uin:%s, nick_name:%s" % (self.uin, self.nick_name))

class Message(models.Model):
    msg_id = models.CharField(max_length=200, blank=False)
    msg_type = models.CharField(max_length=10, blank=False)
    msg_time = models.IntegerField(blank=False)
    msg_from = models.CharField(max_length=100, blank=True)
    msg_to = models.CharField(max_length=100, blank=True)
    msg_url = models.CharField(max_length=500, blank=True)
    msg_text = models.TextField(blank=True)
    msg_bin = models.BinaryField(blank=True)
    msg_json = models.TextField(blank=False)
    msg_uin = models.CharField(max_length=200, blank=False, default='')
    msg_is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=200, blank=True)
    sender_user_name = models.CharField(max_length=200, blank=True)
    sender_nick_name = models.CharField(max_length=200, blank=True)

    @classmethod
    def create(Message, msg, is_group=False):
        msgId = msg['MsgId'] # id
        msgTime = int(msg['CreateTime']) # time
        msgFrom = msg['FromUserName']
        msgTo = msg['ToUserName']
        msgType = msg['Type'] # type
        msgText = None # for plain msg
        msgBin = None # for binary msg (e.g. photo, file, recording...)
        subfilename = ''
        msgUrl = '' # a sharing msg has a url
        is_bin = False

        if msg['Type'] == 'Text':
            msgText = msg['Text']

        elif msg['Type'] == 'Picture' or \
            msg['Type'] == 'Recording' or \
            msg['Type'] == 'Attachment' or \
            msg['Type'] == 'Video':
            msgBin = msg['Text']()
            msgText = msg['FileName']
            is_bin = True

        elif msg['Type'] == 'Card':
            msgText = msg['RecommendInfo']['NickName'] + r" 的名片"

        elif msg['Type'] == 'Map':
            x, y, location = \
                re.search("<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
            if location is None:
                msgText = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
            else:
                msgText = r"" + location

        elif msg['Type'] == 'Sharing':
            msgText = msg['Text']
            msgUrl = msg['Url']
            print("url: %s" % msgUrl)

        elif msg['Type'] == 'Friends':
            msgText = msg['Text']

        # get receiver uin by receiver's user name
        to_wc = get_wc(user_name=msgTo)
        msgUin = to_wc.uin

        group_name = ''
        s_user_name = ''
        s_nick_name = ''
        if is_group:
            group_name = msg['FromUserName']
            s_user_name = msg['ActualUserName']
            s_nick_name = msg['ActualNickName']

        if not is_bin:
            print('text msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_text=msgText, msg_json=msg, msg_uin=msgUin, \
                            msg_is_group=is_group, group_name=group_name, \
                            sender_user_name=s_user_name, sender_nick_name=s_nick_name)
        else:
            print('bin msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_bin=msgBin, msg_json=msg, msg_uin=msgUin, \
                            msg_text=msgText, \
                            msg_is_group=is_group, group_name=group_name, \
                            sender_user_name=s_user_name, sender_nick_name=s_nick_name)

    def __str__(self):
        if self.msg_is_group:
            group = get_group(name=self.group_name)
            return ("group:%s, sender:%s, type:%s" % (group.nick_name, self.sender_nick_name, self.msg_type))
        else:
            to_wc = get_wc(uin=self.msg_uin)
            to_nick = to_wc.nick_name
            return ("id:%s, to:%s, type:%s" % (self.msg_id, to_nick, self.msg_type))

class Group(models.Model):
    name = models.CharField(max_length=200)
    nick_name = models.CharField(max_length=200)

    def __str__(self):
        return ("id:%s, name:%s" % (self.name, self.nick_name))

class NotifyMessage(models.Model):
    to_user_name = models.CharField(max_length=200, blank=False)
    group_name = models.CharField(max_length=200, blank=False)
    msg_time = models.IntegerField(blank=False)

    def __str__(self):
        return ("to:%s, group:%s" % (self.to_user_name, self.group_name))

class WechatMP(models.Model):
    app_id = models.CharField(max_length=18, blank=False)
    app_secret = models.CharField(max_length=32, blank=False)
    access_token = models.CharField(max_length=512, blank=True)
    expire_duration = models.IntegerField(blank=True, default=0)
    access_token_stamp = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return ("ID:%s" % (self.app_id))

class ShortUrl(models.Model):
    openid = models.CharField(max_length=200)
    login_url = models.CharField(max_length=30)

    def __str__(self):
        return ("openid:%s, login_url:%s" % (self.openid, self.login_url))

# DB operation tool functions
def get_group(name=None, nick_name=None):
    if not (name==None and nick_name==None):
        if name:
            group = Group.objects.get(name=name)
        elif nick_name:
            group = Group.objects.get(nick_name=nick_name)
        print("[get Group] name = %s, nick_name = %s" % (name, nick_name))
        return group

def get_group_nick_name(group_name):
    group = get_group(name=group_name)
    if group:
        return group.nick_name

def get_wc(uin=None, user_name=None, openid=None):
    if not (uin==None and user_name==None and openid==None):
        try:
            if uin:
                print("uin=%s" % uin)
                wc = WechatClient.objects.get(uin=uin)
            elif user_name:
                wc = WechatClient.objects.get(user_name=user_name)
            elif openid:
                wc = WechatClient.objects.get(openid=openid)
            print("[get wechat client] openid = %s, uin = %s, username = %s" % (openid, uin, user_name))
        except WechatClient.DoesNotExist:
            wc = None
        return wc

def get_msg(msg_id=None):
    msg = None
    msg_qs = Message.objects.filter(msg_id=msg_id)
    if msg_qs.count() == 1:
        msg = msg_qs.get(msg_id=msg_id)
    return msg

def get_nick_name(user_name):
    wc = get_wc(user_name=user_name)
    if wc:
        return wc.nick_name
