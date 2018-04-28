# -*- coding:utf8 -*-
import os, time, re, io, sys, shutil, pytz, datetime
import requests
import json
import tempfile
import logging

# ASR
from pydub import AudioSegment
from .aliyun_asr.aliyun_voice_asr import sendAsrPost

from .site_package import itchat
from .site_package.itchat.content import *
from Wechat_Assisant.models import *
from django.conf import settings
from .constant import Constant

# Get an instance of a logger
logger = logging.getLogger('web-logger')

sendFilePrefixDict = {'Attachment': '@fil@', 'Picture': '@img@', 'Video': '@vid@'}

def audio2text(audio_path, audio_format="pcm", sample_rate="8000"):
	url = settings.ALIYUN_ASR_URL
	ak_id = settings.ALIYUN_ACCESS_KEY_ID
	ak_secret = settings.ALIYUN_ACCESS_KEY_SECRET
	try:
		res = sendAsrPost(audio_path, audio_format, sample_rate, url, ak_id, ak_secret)
		if res.status_code == requests.codes.ok:
			res_json = json.loads(res.content)
			result = res_json['result']
	except Exception as e:
		print(e)
		result = "[抱歉，语音转文字功能暂时不可用，请听语音档]"
	return result

def t_readable(t):
	sh = pytz.timezone('Asia/Shanghai')
	dt = datetime.datetime.strptime(time.ctime(int(t)), "%a %b %d %H:%M:%S %Y")
	t_loc = sh.localize(dt)
	t_read = t_loc.strftime('%Y-%m-%d %H:%M:%S %Z%z')
	return t_read

def get_group_notify_context(notify_seg):
	returnList = []
	begin_notify_msg = notify_seg['begin']
	last_notify_msg = notify_seg['last']
	to_uin = begin_notify_msg.uin
	group_name = begin_notify_msg.group_name
	start = begin_notify_msg.msg_time - 60
	end = last_notify_msg.msg_time + 60
	close_old_connections()
	group_msg_qs = Message.objects.filter(msg_is_group=True, group_name=group_name, \
											msg_uin=to_uin, msg_time__range=(start, end))
	# concatenate messages, converting recording to text
	showntime = t_readable(begin_notify_msg.msg_time)
	if group_msg_qs.count() > 0:
		group_nick_name = get_group_nick_name(begin_notify_msg.group_name)
		send_text = u'[' + showntime + '] 你在群聊 "'+ group_nick_name + u'" 中收到提及你的消息：\n'
		has_audio = False
		has_pic = False
		for msg in group_msg_qs.iterator():
			if msg.msg_type == 'Recording':
				has_audio = True
				result = ''
				with tempfile.NamedTemporaryFile() as tmp:
					audio = io.BytesIO(msg.msg_bin)
					AudioSegment.from_mp3(audio).export(tmp.name, format='wav')
					result = audio2text(tmp.name)
					print("group recording ASR result:" + result)
				content = result + '[转文字]'
			elif msg.msg_type == 'Picture':
				has_pic = True
				content = '[Picture]'
			elif msg.msg_type == 'Text':
				content = '[可能是群公告]' + msg.msg_text if msg.is_notice else msg.msg_text
			content = '[撤回消息]' + content if msg.revoked else content
			send_text += msg.sender_nick_name + u': ' + content + u'\n'
		if has_audio:
			send_text += u"\n(以上包含语音转文字后的结果，如有需要请到群內查看)"
		if has_pic:
			send_text += u"\n(上下文中的图片没有显示，如有需要请到群內查看)"
		returnList.append(send_text)
	return returnList

# send all groups' notify messages to filehelper
def assisant_send_group_notify(itchat_ins):
	print("Send group notify messages to filehelper")
	uin = (itchat_ins.search_friends())['Uin']
	close_old_connections()
	notify_msg_qs = NotifyMessage.objects.filter(uin=uin)
	if notify_msg_qs.count()==0:
		itchat_ins.send(u'没有提及你的群消息', toUserName='filehelper')
		return
	else:
		msg_list = []
		notify_msg_seg_list = []
		pre_msg_time = notify_msg_qs[0].msg_time
		# find consecutive notifiction mgs
		begin = notify_msg_qs[0]
		last = notify_msg_qs[0]
		for notify_msg in notify_msg_qs.iterator():
			if notify_msg.msg_time - pre_msg_time > 60:
				notify_msg_seg_list.append(dict({'begin': begin, 'last':last}))
				begin = notify_msg
			last = notify_msg
			pre_msg_time = notify_msg.msg_time
		notify_msg_seg_list.append(dict({'begin': begin, 'last':last}))
		# generate notification context
		for notify_seg in notify_msg_seg_list:
			msg_list += get_group_notify_context(notify_seg)
		# delete notify msg
		close_old_connections()
		for notify_msg in notify_msg_qs.iterator():
			notify_msg.delete()
		# send all context to file helper
		for text in msg_list:
			itchat_ins.send(text, toUserName='filehelper')
	return

# trigger different assisant functions according to the msg content
def assisant_control_menue(msg, assistant):
	msg_from = msg['FromUserName']
	print('client(oid=%s) sent a robot control message(type=%s)' % (assistant.openid, msg['Type']))
	if msg['Type'] == 'Text':
		msgContent = msg['Text']
		if msgContent == '@':
			assisant_send_group_notify(assistant.itchat_ins)
		elif re.match('del', msgContent, re.IGNORECASE):
			assistant.del_client_records()
			print('client(openid=%s) require to delete his/her records, finished' % assistant.openid)
		elif re.match('friend', msgContent, re.IGNORECASE):
			assistant.itchat_ins.send(Constant.CHECK_FRIEND_MSG, 'filehelper')
		else:
			assistant.itchat_ins.send(Constant.UNSUPPORTED_CONTROL_MSG, toUserName='filehelper')
			print('It is an unsupported control message.')
	elif msg['Type'] == 'Card':
		assistant.itchat_ins.send(Constant.CHECK_FRIEND_START_MSG, toUserName='filehelper')
		friend_status = assistant.get_friend_status(msg['RecommendInfo'])
		assistant.itchat_ins.send(friend_status, 'filehelper')
	else:
		print('It is an unsupported type of control message.')

#收到note类消息，判断是不是撤回并进行相应操作
def note_handler(msg, itchat_ins):
	if msg['MsgType'] == 10002:
		# check weather it is a revoking note msg send from wechat system to the revoked
		# which means I ignore revoking note like "you revoked a message"
		for you in Constant.YOU_DICT:
			if you in msg['Text']:
				return
		revoked_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
		revoked_msg = get_msg(msg_id=revoked_msg_id)
		showntime = t_readable(revoked_msg.msg_time)
		if revoked_msg.msg_is_group:
			from_nick_name = revoked_msg.sender_nick_name
			group_nick_name = get_group_nick_name(revoked_msg.group_name)
			if group_nick_name == None:
				group_nick_name = u"一个群"
			else:
				group_nick_name = '"' + group_nick_name + '"'
			msg_send = from_nick_name \
					   + u" 于[" + showntime + u"], " \
					   + u"在" + group_nick_name + u"中, " \
					   + u"撤回了一条 [" + revoked_msg.msg_type + u"] 消息, 内容如下:"
		else:
			from_nick_name = itchat_ins.search_friends(userName=msg['FromUserName'])['NickName']
			msg_send = u"您的好友：" \
					   + from_nick_name \
					   + u"  在 [" + showntime \
					   + u"], 撤回了一条 [" + revoked_msg.msg_type + u"] 消息, 内容如下:"

		print("%s revoked a msg: %s" % (from_nick_name, revoked_msg.msg_type))

		is_bin_msg = False
		if revoked_msg.msg_type == "Text":
			msg_send += revoked_msg.msg_text
		elif revoked_msg.msg_type == "Sharing":
			msg_send += revoked_msg.msg_text + u", 链接: " + revoked_msg.msg_url
		elif revoked_msg.msg_type == 'Picture' \
			or revoked_msg.msg_type == 'Video' \
			or revoked_msg.msg_type == 'Attachment':
			is_bin_msg = True
			sendMsgPrefix = sendFilePrefixDict[revoked_msg.msg_type]
			if revoked_msg.msg_type == 'Attachment':
				msg_send += u' （原文件名为 ' + revoked_msg.msg_text + u'）'
		elif revoked_msg.msg_type == 'Recording':
			is_bin_msg = True
			with tempfile.NamedTemporaryFile() as tmp:
				audio = io.BytesIO(revoked_msg.msg_bin)
				AudioSegment.from_mp3(audio).export(tmp.name, format='wav')
				result = audio2text(tmp.name)
				print("ASR result:" + result)
				msg_send += u'\n' + result
				msg_send += u"\n(以上语音转文字后的结果，如有需要请查听以下的语音档)"
			sendMsgPrefix = sendFilePrefixDict['Attachment']
		else:
			msg_send += u"Error: Unsupported Type!"

		# send revoked msg to filehelper to notify the user
		itchat_ins.send(msg_send, toUserName='filehelper')
		if is_bin_msg:
			with tempfile.NamedTemporaryFile() as tmp:
				tmp.write(revoked_msg.msg_bin)
				tmp.seek(0)
				subfilename = revoked_msg.msg_text[revoked_msg.msg_text.rfind('.'):]
				newPath = tmp.name + subfilename
				os.rename(tmp.name, newPath)
				r = itchat_ins.send('%s%s' % (sendMsgPrefix, newPath), toUserName='filehelper')
				os.rename(newPath, tmp.name)
		revoked_msg.revoked = True
		revoked_msg.save()

#将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
#没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
# @itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
def msg_handler(msg, assistant):
	itchat_ins = assistant.itchat_ins
	# ignore the msg which a user send to himself/herself
	if msg['FromUserName'] == msg['ToUserName']:
		return;
	# it maybe is a robot control message
	if msg['ToUserName'] == 'filehelper':
		assisant_control_menue(msg, assistant)
		return
	# print(msg)
	# ignore msg sent by a user here in the client pool and receive it again
	# detail:	wechat will send msg to both sender and receiver
	# 			the msg sender got a msg containing a from_user_name that my server know
	# 			but a to_user_name that my server doesn't know
	# 			user this feature to filter the msg turned back to the sender
	if WechatClient.objects.filter(user_name=msg['ToUserName']).count() == 0:
		close_old_connections()
		msg_obj = Message.create(msg, send=True);
		msg_obj.save()
		return

	# print('%s received a msg' % get_nick_name(msg['ToUserName']))

	if msg['Type'] == 'Note':
		note_handler(msg, itchat_ins)
		return

	# insert this msg to DB
	close_old_connections()
	msg_obj = Message.create(msg);
	msg_obj.save()

# group texts handling function
# Issues: group msg will not boardcast to the sender, so we miss part of the notify context
# TO-DO: 1. Can we tackle the boardcast redundancy? boardcast msg will be sent to every user in a group
#			if we have multiple clients in a same group, then a same msg will repeated in our DB
# 		2. How can we identical different groups? now a group will create a new model after users login again
# @itchat.msg_register([TEXT, RECORDING, PICTURE], isGroupChat=True)
def HandleGroupMsg(msg, assistant):
	itchat_ins = assistant.itchat_ins
	uin = (itchat_ins.search_friends())['Uin']

	# initial a group or update nick name of a gorup
	group_name = msg['FromUserName'] if '@@' in msg['FromUserName'] else msg['ToUserName']
	group_nick_name = msg['User']['NickName']
	new_values = {'uin': uin, 'name':group_name, 'nick_name':group_nick_name}
	close_old_connections()
	group_obj, created = Group.objects.update_or_create(uin=uin, name=group_name, defaults=new_values,)

	# save but don't process the one send from the cilent and receive by the group(which ToUserName is the group itself)
	if '@@' in msg['ToUserName']:
		close_old_connections()
		msg_obj = Message.create(msg, is_group=True, send=True);
		msg_obj.save()
		return

	if msg['Type'] == 'Note':
		note_handler(msg, itchat_ins)
		return

	# create messages model
	close_old_connections()
	msg_obj = Message.create(msg, is_group=True);
	msg_obj.save()

	# check whether it is a notify message
	if msg_obj.is_at or msg_obj.is_notice:
		msg_id = msg['MsgId']
		to_user_name = msg['ToUserName']
		msg_time = msg['CreateTime']
		uin = (itchat_ins.search_friends())['Uin']
		close_old_connections()
		notify_msg = NotifyMessage(uin=uin, msg_id=msg_id, group_name=group_name, msg_time=msg_time)
		notify_msg.save()
		# print('%s @%s in a group' % (msg['ActualNickName'], get_display_name_group(msg, to_user_name)))

# massive platfrom msgs handler
def mp_msg_handler(msg, assistant):
	# print(msg)
	# create messages model
	close_old_connections()
	msg_obj = Message.create(msg, is_mp=True);
	msg_obj.save()
