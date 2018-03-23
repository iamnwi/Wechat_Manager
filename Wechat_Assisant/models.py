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
    msg_url = models.CharField(max_length=100, blank=True)
    msg_text = models.TextField(blank=True)
    msg_bin = models.BinaryField(blank=True)
    msg_json = models.TextField(blank=False)

    def __str__(self):
        wc = WechatClient.objects.get(user_name=self.msg_to)
        to_nick = wc.nick_name
        if self.msg_type == 'Text' or self.msg_type == 'Sharing':
            content = self.msg_text
        else:
            content = 'BIN'
        return ("id:%s, to:%s, content:%s" % (self.msg_id, to_nick, content))
