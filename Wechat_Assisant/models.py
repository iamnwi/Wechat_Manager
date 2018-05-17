# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
import re

# Create your models here.
class WechatClient(models.Model):
    openid = models.CharField(max_length=200, default='None')
    uin = models.CharField(max_length=200, blank=True)
    user_name = models.CharField(max_length=200, default='None')
    nick_name = models.CharField(max_length=200, default='None')
    icon = models.BinaryField(blank=True)
    online = models.BooleanField(default=False)
    # login status
    # 0: initial status, 200: logined, 201: wait for scan, 408: qrcode timeout
    login_status = models.IntegerField(blank=False, default='0')
    # cookies for push login
    host = models.CharField(max_length=50, default='None')
    webwxuvid = models.CharField(max_length=100, default='None')
    webwx_auth_ticket = models.CharField(max_length=190, default='None')
    # data
    group_list = models.TextField(default='[]')
    friend_list = models.TextField(default='[]')
    mp_list = models.TextField(default='[]')

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
    msg_is_mp = models.BooleanField(default=False)
    group_name = models.CharField(max_length=200, blank=True)
    sender_user_name = models.CharField(max_length=200, blank=True)
    sender_nick_name = models.CharField(max_length=200, blank=True)
    revoked = models.BooleanField(default=False)
    is_notice = models.BooleanField(default=False)
    is_at = models.BooleanField(default=False)
    send = models.BooleanField(default=False)

    @classmethod
    def create(Message, msg, is_group=False, is_mp=False, send=False):
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

        elif msg['Type'] == 'Friends':
            msgText = msg['Text']

        # get receiver uin by receiver's user name
        if send:
            wc = get_wc(user_name=msgFrom)
        else:
            wc = get_wc(user_name=msgTo)
        msgUin = wc.uin if wc is not None else 'Unknown'

        group_name = ''
        s_user_name = ''
        s_nick_name = ''
        is_at = False
        is_notice = False
        if is_group:
            group_name = msg['FromUserName'] if '@@' in msg['FromUserName'] else msg['ToUserName']
            s_user_name = msg['ActualUserName']
            s_nick_name = msg['ActualNickName']
            if send is False:
                # check wheather it is a notification group msg
                # 1. check @NickName
                # 2. check @DisplayName(a name defined for a group)
                if msg['Type']=='Text':
                    msg_content = msg['Text']
                    # notification msg included '@someone'
                    if '@' in msg_content:
                        user_name = msg['ToUserName']
                        nick_name = get_nick_name(user_name)
                        if u'@'+nick_name in msg_content:
                            is_at = True
                        display_name = get_display_name_group(msg, user_name)
                        # print("your display name is %s" % display_name)
                        if display_name != None and '@' + display_name in msg_content:
                            is_at = True
                    # group notice
                    if not is_at:
                        chat_room_owner_re = re.search(r"'ChatRoomOwner': '([^']*)'}", str(msg))
                        if chat_room_owner_re:
                            chat_room_owner = chat_room_owner_re.group(1)
                            # print('owner=%s' % chat_room_owner)
                            if msg['ActualUserName'] == chat_room_owner and len(msg_content) > 30:
                                is_notice = True

        if not is_bin:
            # print('text msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_text=msgText, msg_json=msg, msg_uin=msgUin, \
                            msg_is_group=is_group, group_name=group_name, \
                            sender_user_name=s_user_name, sender_nick_name=s_nick_name, \
                            is_notice=is_notice, is_at=is_at, msg_is_mp=is_mp, send=send)
        else:
            # print('bin msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_bin=msgBin, msg_json=msg, msg_uin=msgUin, \
                            msg_text=msgText, \
                            msg_is_group=is_group, group_name=group_name, \
                            sender_user_name=s_user_name, sender_nick_name=s_nick_name, \
                            is_notice=is_notice, is_at=is_at, msg_is_mp=is_mp, send=send)

    def __str__(self):
        if self.msg_is_group:
            group = get_group(name=self.group_name)
            return ("group:%s, sender:%s, type:%s" % (group.nick_name, self.sender_nick_name, self.msg_type))
        else:
            to_wc = get_wc(uin=self.msg_uin)
            to_nick = to_wc.nick_name if to_wc is not None else 'Unknown'
            return ("id:%s, to:%s, type:%s" % (self.msg_id, to_nick, self.msg_type))

class Group(models.Model):
    name = models.CharField(max_length=200)
    uin = models.CharField(max_length=200, blank=False, default='0')
    nick_name = models.CharField(max_length=200)

    def __str__(self):
        return ("uin:%s, id:%s, name:%s" % (self.uin, self.name, self.nick_name))

class NotifyMessage(models.Model):
    uin = models.CharField(max_length=200, blank=False, default='0')
    msg_id = models.CharField(max_length=200, blank=False, default="0")
    group_name = models.CharField(max_length=200, blank=False)
    msg_time = models.IntegerField(blank=False)

    def __str__(self):
        return ("to:%s, group:%s" % (self.uin, self.group_name))

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

    def __str__(self):
        return ("openid:%s" % self.openid)

class Analyze(models.Model):
    openid = models.CharField(max_length=200, blank=False)
    result = models.TextField(blank=False)
    year = models.IntegerField(blank=False, default=2018)
    weeknum = models.IntegerField(blank=False)

    def __str__(self):
        return ("openid:%s" % self.openid)

# DB operation tool functions
def get_group(name=None, nick_name=None):
    close_old_connections()
    if not (name==None and nick_name==None):
        if name:
            group = Group.objects.get(name=name)
        elif nick_name:
            group = Group.objects.get(nick_name=nick_name)
        # print("[get Group] name = %s, nick_name = %s" % (name, nick_name))
        return group

def get_group_nick_name(group_name):
    group = get_group(name=group_name)
    if group:
        return group.nick_name

def get_wc(uin=None, user_name=None, openid=None):
    close_old_connections()
    if not (uin==None and user_name==None and openid==None):
        try:
            if uin:
                wc = WechatClient.objects.get(uin=uin)
            elif user_name:
                wc = WechatClient.objects.get(user_name=user_name)
            elif openid:
                wc = WechatClient.objects.get(openid=openid)
        except WechatClient.DoesNotExist:
            print("[get wechat client] FAIL: DoesNotExist -- openid = %s, uin = %s, username = %s" % (openid, uin, user_name))
            wc = None
        return wc

def get_msg(msg_id=None):
    close_old_connections()
    msg = None
    msg_qs = Message.objects.filter(msg_id=msg_id, send=False)
    if msg_qs.count() == 1:
        msg = msg_qs.get(msg_id=msg_id)
    return msg

def get_nick_name(user_name):
    wc = get_wc(user_name=user_name)
    if wc:
        return wc.nick_name

def analyze_obj_get(openid, year, weeknum):
    qs = Analyze.objects.filter(openid=openid, year=year, weeknum=weeknum)
    if qs.count() == 1:
        return qs[0]

# find display name to the specific user in the group where the message comes from.
def get_display_name_group(msg, user_name):
    member_content = re.search(r"<ContactList: \[<ChatroomMember: \{(.*)\}>]>", str(msg))
    if member_content != None:
        users = re.findall(r"'UserName': '([^']*)", member_content.group(1))
        displays = re.findall(r"'DisplayName': '([^']*)", member_content.group(1))
        if users != None and displays != None:
            user2nick = dict(zip(users, displays))
            for (user, nick) in user2nick.items():
                if user == user_name and nick != '':
                    return nick

# solve issue: OperationalError: (2006, 'MySQL server has gone away')
from django.db import connections

def close_old_connections():
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()
