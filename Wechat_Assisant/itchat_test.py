# -*- coding:utf8 -*-
import re
import sys
import time
import os
import shutil
import requests
import json

# import itchat
# from itchat.content import *
# from ..site_package import myitchat
from site_package import itchat
from site_package.itchat.content import *
# from .. import site_package.myitchat

@itchat.msg_register(TEXT, isGroupChat=True)
def text_reply(msg):
    print('received a msg from a group')
    if msg.isAt:
        print("someone @ you in a group #1")
    if msg['isAt']:
        print("someone @ you in a group")

def qrFun(uuid, qrcode, **extra_dict):
    print(uuid)
    print(extra_dict)
    with open('../static/imgs/qrcode/%s.png' % uuid, 'wb+') as f:
        f.write(qrcode)

#itchat.auto_login(picDir = './QRcode/qr.png', qrCallback = qrFun)
itchat.auto_login(qrCallback=qrFun)
# r = itchat.send('hi', toUserName='filehelper')
# print(r)
# filePath = '@fil@./ReceivedMsg/Attachment/pkugo.ppt'
# r = itchat.send(filePath, toUserName='filehelper')
# print(r)
# itchat.run()
