# -*- coding:utf8 -*-
import os
import time
import re
import sys
import shutil
import requests
import json
import random

from .site_package import itchat
from .site_package.itchat.content import *
from Wechat_Assisant.models import *

def turn_offline():
	uin = (itchat.search_friends())['Uin']
	wc = get_wc(uin=uin)
	if wc:
		wc.online = False
		wc.save()
		print("[turn_offline] client(uid=%s) turn offline successfully" % (wc.uin))
		return True
	return False

#收到note类消息，判断是不是撤回并进行相应操作
def note_handler(msg):
	if re.search(r"\<replacemsg\>\<\!\[CDATA\[[^你]*撤回了一条消息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
		or re.search(r"\<replacemsg\>\<\!\[CDATA\[[^你]*回收一則訊息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
		or re.search(r"\<replacemsg\>\<\!\[CDATA\[[^you]*recalled a message\.\]\]\>\<\/replacemsg\>", msg['Content']) != None:
		revoked_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
		revoked_msg = get_msg(msg_id=revoked_msg_id)
		showntime = time.ctime(int(revoked_msg.msg_time))
		from_nick_name = itchat.search_friends(userName=msg['FromUserName'])['NickName']

		print("%s revoked a msg: %s" % (from_nick_name, revoked_msg.msg_type))
		msg_send = u"您的好友：" \
				   + from_nick_name \
				   + u"  在 [" + showntime \
				   + u"], 撤回了一条 [" + revoked_msg.msg_type + u"] 消息, 内容如下:"

		if revoked_msg.msg_type == "Text":
			msg_send += revoked_msg.msg_text
		elif revoked_msg.msg_type == "Sharing":
			msg_send += u", 链接: " + revoked_msg.msg_url
		else:
			msg_send += u"Error: Unsupported Type!"

		# send revoked msg to filehelper to notify the user
		itchat.send(msg_send, toUserName='filehelper')

#将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
#没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
def msg_handler(msg):
	# ignore msg sent by a user here in client pool and receive it again
	# detail:	wechat will send msg to both sender and receiver
	# 			the msg sender got contain a from_user_name that my server know
	# 			but a to_user_name that my server doesn't know
	# 			user this feature to filter the msg turned back to the sender
	if WechatClient.objects.filter(user_name=msg['ToUserName']).count() == 0:
		return
	# ignore the msg which a user send to himself/herself
	if msg['FromUserName'] == msg['ToUserName']:
		return;
	# it maybe is a robot control message
	if msg['ToUserName'] == 'filehelper':
		robotControl(msg)
		return

	print('%s received a msg' % get_nick_name(msg['ToUserName']))

	if msg['Type'] == 'Note':
		note_handler(msg)
		return

	# insert this msg to DB
	msg_obj = Message.create(msg);
	msg_obj.save()
