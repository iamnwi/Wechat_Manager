# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from Wechat_Assisant.models import *

admin.site.register(WechatClient)
admin.site.register(Message)
admin.site.register(Group)
admin.site.register(NotifyMessage)
