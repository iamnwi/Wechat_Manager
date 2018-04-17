# -*- coding:utf8 -*-
import os, time, re, io, sys, shutil
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

def get_group_notify_context(notify_seg):
	returnList = []
	begin_notify_msg = notify_seg['begin']
	last_notify_msg = notify_seg['last']
	to_user_name = begin_notify_msg.to_user_name
	group_name = begin_notify_msg.group_name
	start = begin_notify_msg.msg_time - 60
	end = last_notify_msg.msg_time + 60
	close_old_connections()
	group_msg_qs = Message.objects.filter(msg_is_group=True, group_name=group_name, \
											msg_to=to_user_name, msg_time__range=(start, end))
	# concatenate messages, converting recording to text
	if group_msg_qs.count() > 0:
		group_nick_name = get_group_nick_name(begin_notify_msg.group_name)
		send_text = u'您在群聊 "'+ group_nick_name + u'" 中收到和您有关的消息：\n'
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
				content = msg.msg_text
			send_text += msg.sender_nick_name + u': ' + content + u'\n'
		if has_audio:
			send_text += u"\n(以上包含语音转文字后的结果，如有需要请到群內查看)"
		if has_pic:
			send_text += u"\n(上下文中的图片没有显示，如有需要请到群內查看)"
		returnList.append(send_text)
	return returnList

# send all groups' notify messages to filehelper
def assisant_send_group_notify(user_name, itchat_ins):
	print("Send group notify messages to filehelper")
	close_old_connections()
	notify_msg_qs = NotifyMessage.objects.filter(to_user_name=user_name)
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
			notify_msg.delete()
		# send all context to file helper
		for text in msg_list:
			itchat_ins.send(text, toUserName='filehelper')
	return

# trigger different assisant functions according to the msg content
def assisant_control_menue(msg, itchat_ins):
	msg_from = msg['FromUserName']
	print('received a robot control message')
	if msg['Type'] == 'Text':
		msgContent = msg['Text']
		if msgContent == '@':
			assisant_send_group_notify(msg_from, itchat_ins)
		else:
			print('It is an unsupported control message.')
	else:
		print('It is an unsupported type of control message.')

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

# check whether it is a notify message
# 1. check @all
# 2. check @NickName
# 3. check @DisplayName(a name defined for a group)
def check_group_notify(msg, group_name):
	if not msg['Type']=='Text':
		return False
	print('checkGroupNotify')
	msg_content = msg['Content']
	if '@' in msg_content:
		if u'@所有人' in msg_content or\
			u'@all' in msg_content:
			return True
		else:
			user_name = msg['ToUserName']
			nick_name = get_nick_name(user_name)
			if u'@'+nick_name in msg_content:
				return True
			display_name = get_display_name_group(msg, user_name)
			print("your display name is %s" % display_name)
			if display_name != None and '@' + display_name in msg_content:
				return True
	else:
		return False

#收到note类消息，判断是不是撤回并进行相应操作
def note_handler(msg, itchat_ins):
	if msg['MsgType'] == 10002:
		# check weather it is a revoking note msg send from wechat system to the revoked
		# which means I ignore revoking note like "you revoked a message"
		for you in settings.YOU_DICT:
			if you in msg['Text']:
				return
		revoked_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
		revoked_msg = get_msg(msg_id=revoked_msg_id)
		showntime = time.ctime(int(revoked_msg.msg_time))
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
				print(r)
		revoked_msg.revoked = True
		revoked_msg.save()

#将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
#没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
# @itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
def msg_handler(msg, itchat_ins):
	# ignore the msg which a user send to himself/herself
	if msg['FromUserName'] == msg['ToUserName']:
		return;
	# it maybe is a robot control message
	if msg['ToUserName'] == 'filehelper':
		assisant_control_menue(msg, itchat_ins)
		return
	# ignore msg sent by a user here in the client pool and receive it again
	# detail:	wechat will send msg to both sender and receiver
	# 			the msg sender got a msg containing a from_user_name that my server know
	# 			but a to_user_name that my server doesn't know
	# 			user this feature to filter the msg turned back to the sender
	if WechatClient.objects.filter(user_name=msg['ToUserName']).count() == 0:
		return

	print('%s received a msg' % get_nick_name(msg['ToUserName']))

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
def HandleGroupMsg(msg, itchat_ins):
    # drop the one send from the cilent and receive by the group(which to user is the group itself)
	if '@@' in msg['ToUserName']:
		return
	print('%s received a group msg' % get_nick_name(msg['ToUserName']))

	# initial a group or update nick name of a gorup
	group_name = msg['FromUserName']
	group_nick_name = msg['User']['NickName']
	close_old_connections()
	group_qs = Group.objects.filter(name=msg['FromUserName'])
	if group_qs.count() == 0:
		group_obj = Group(name=group_name, nick_name=group_nick_name)
		group_obj.save()
	elif group_qs.count() == 1 and group_nick_name != group_qs.get(name=group_name).nick_name:
		group_obj = group_qs.get(name=group_name)
		group_obj.nick_name = group_nick_name
		group_obj.save()

	if msg['Type'] == 'Note':
		note_handler(msg, itchat_ins)
		return

	# create messages model
	close_old_connections()
	msg_obj = Message.create(msg, is_group=True);
	msg_obj.save()

	# check whether it is a notify message
	if check_group_notify(msg, group_name):
		msg_id = msg['MsgId']
		to_user_name = msg['ToUserName']
		msg_time = msg['CreateTime']
		close_old_connections()
		notify_msg = NotifyMessage(msg_id=msg_id, to_user_name=to_user_name, group_name=group_name, msg_time=msg_time)
		notify_msg.save()
		print('%s @%s in a group' % (msg['ActualNickName'], get_display_name_group(msg, to_user_name)))
