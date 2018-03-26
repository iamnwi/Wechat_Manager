# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class WechatClient(models.Model):
    uin = models.CharField(max_length=200, default='NONE')
    user_name = models.CharField(max_length=200, default='NONE')
    nick_name = models.CharField(max_length=200, default='NONE')
    online = models.BooleanField(default=False)

    def __str__(self):
        return ("uin:%s, nick_name:%s" % (self.uin, self.nick_name))

class Message(models.Model):
    msg_id = models.CharField(max_length=200, blank=False)
    msg_type = models.CharField(max_length=10, blank=False)
    msg_time = models.CharField(max_length=50, blank=False)
    msg_from = models.CharField(max_length=100, blank=False)
    msg_to = models.CharField(max_length=100, blank=False)
    msg_url = models.CharField(max_length=500, blank=True)
    msg_text = models.TextField(blank=True)
    msg_bin = models.BinaryField(blank=True)
    msg_json = models.TextField(blank=False)
    msg_uin = models.CharField(max_length=200, blank=False, default='')

    @classmethod
    def create(Message, msg):
        msgId = msg['MsgId'] # id
        msgTime = msg['CreateTime'] # time
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

        if not is_bin:
            print('text msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_text=msgText, msg_json=msg, msg_uin=msgUin)
        else:
            print('bin msg')
            return Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
                            msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
                            msg_bin=msgBin, msg_json=msg, msg_uin=msgUin, \
                            msg_text=msgText)

    def __str__(self):
        to_wc = get_wc(uin=self.msg_uin)
        to_nick = to_wc.nick_name

        if self.msg_type == 'Text' or self.msg_type == 'Sharing':
            content = self.msg_text
        else:
            content = 'BIN'
        return ("id:%s, to:%s, content:%s" % (self.msg_id, to_nick, content))
        return ("id:%s" % self.msg_id)

# DB operation tool functions
def get_wc(uin=None, user_name=None):
    if not (uin==None and user_name==None):
        if uin:
            wc = WechatClient.objects.get(uin=uin)
        elif user_name:
            wc = WechatClient.objects.get(user_name=user_name)
        print("[get wechat client] uin = %s, username = %s" % (uin, user_name))
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
