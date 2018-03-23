# -*- coding:utf8 -*-
import os
import time
from site_package import itchat
from site_package.itchat.content import *

#ClearTimeOutMsg用于清理消息字典，把超时消息清理掉
#为减少资源占用，此函数只在有新消息动态时调用
def ClearTimeOutMsg(msgDict, timestamp):
	# print("ClearTimeOutMsg")
	# currentTime = time.time()
	# print('current time: %f', currentTime)
	if msgDict.__len__() > 0:
		for msgId in list(msgDict): #由于字典在遍历过程中不能删除元素，故使用此方法
			if timestamp - msgDict.get(msgId)["msgTime"] > 130.0: #超时两分钟
				item = msgDict.pop(msgId)
				# if item['msgType'] == "Picture" \
				# 	or item['msgType'] == "Recording" \
				# 	or item['msgType'] == "Video" \
				# 	or item['msgType'] == "Attachment":
				# 	print("要删除的文件：", item['msgContent'])
				# 	os.remove(item['msgContent'])

# find your display name in the group where the message comes from.
def myDisplayNameInGroup(msg):
	memberContent = re.search(r"<ContactList: \[<ChatroomMember: \{(.*)\}>]>", str(msg))
	if memberContent != None:
		print(memberContent.group(1))
		users = re.findall(r"u'UserName': u'([^']*)", memberContent.group(1).encode('utf-8'))
		displays = re.findall(r"u'DisplayName': u'([^']*)", memberContent.group(1).encode('utf-8'))
		if users != None and displays != None:
			user2nick = dict(zip(users, displays))
			for (user, nick) in user2nick.items():
				user = user.decode('unicode-escape')
				if user == myUserName:
					nick = nick.decode('unicode-escape')
					return nick

def getGroupDisplayName(groupID):
	info = itchat.search_chatrooms(name=groupID)
	print(info)

# check whether it is a notify message
# 1. check @all
# 2. check @NickName
# 3. check @DisplayName(a name defined for a group)
def checkGroupNotify(msg, groupID):
	print('checkGroupNotify')
	msgContent = msg['Content']
	if '@' in msgContent:
		if u'@所有人' in msgContent or\
			u'@all' in msgContent or\
			'@' + myNickName in msgContent:
			return True
		else:
			itchat.update_chatroom(groupID)
			displayName = myDisplayNameInGroup(msg)
			if displayName != None and '@' + displayName in msgContent:
				return True
	else:
		return False

def getGroupNotifyContext():
	returnList = []
	for groupID, value in groupDict.items():
		singleMsgList = value.singleMsg
		for msg in singleMsgList:
			groupDisplayName = getGroupDisplayName(groupID)
			tempText = u'您在群聊 "'+ value.groupNickName + u'" 中收到和您有关的消息：\n'
			contextList = msg.preText + [(msg.text, msg.user, 'Text')] + msg.nextText
			# concatenate messages, converting recording to text
			hasConverted = False
			for message in contextList:
				print(message)
				if message[2] == 'Recording':
					audioFileName = message[0].split('/')[-1].split('.')[0]
					result = audio2text(convert(message[0], "./RevokedMsg/converted/"+audioFileName+".wav"))
					print("group msg ASR result:" + result)
					content = result + u'(转文字)'
					hasConverted = True
					print(u"删除文件：" + message[0])
					os.remove(message[0])
				else:
					content = message[0]
				if TextSummaryEnable and len(content) > TextSummaryThreshold:
					content = '\n'.join(textSummarization(content))
				tempText += message[1] + u': ' + content + u'\n'
			if hasConverted:
				tempText += u'以上包含语音转文字后的结果，如有需要请到群内查听'
			returnList.append(tempText)
	return returnList

#收到note类消息，判断是不是撤回并进行相应操作
def HandleNote(self, msg):
	print("%s received a note msg" % self.NickName)

	# if not os.path.exists("./RevokedMsg/"):
	# 	os.mkdir("./RevokedMsg/")

	print(msg['Content'])
	if re.search(r"\<replacemsg\>\<\!\[CDATA\[.*撤回了一条消息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
		or re.search(r"\<replacemsg\>\<\!\[CDATA\[.*回收一則訊息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
		or re.search(r"\<replacemsg\>\<\!\[CDATA\[.*recalled a message\.\]\]\>\<\/replacemsg\>", msg['Content']) != None:
		print("Revoke a message")
		oldMsgId = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
		oldMsg = msgDict.get(oldMsgId, {})
		msgSend = u"您的好友：" \
				   + oldMsg.get('msgFrom') \
				   + u"  在 [" + oldMsg.get('msgTimeToUser') \
				   + u"], 撤回了一条 [" + oldMsg['msgType'] + u"] 消息, 内容如下:"

		needSendFile = False
		print(oldMsg['msgType'])
		if oldMsg['msgType'] == "Text":
			msgSend += oldMsg['msgContent']
		elif oldMsg['msgType'] == "Sharing":
			msgSend += u", 链接: " + oldMsg.get('msgUrl', None)
		# elif oldMsg['msgType'] == 'Recording':
		# 	needSendFile = True
		# 	audioFileName = oldMsg['msgContent'].split('/')[-1].split('.')[0]
		# 	result = audio2text(convert(oldMsg['msgContent'], "./RevokedMsg/converted/"+audioFileName+".wav"))
		# 	print("ASR result:" + result)
		# 	msgSend += u'\n' + result
		# 	msgSend += u"\n 以上语音转文字后的结果，如有需要请查听 ./RevokedMsg/" + audioFileName
		# 	sendMsgPrefix = sendFilePrefixDict['Attachment']
		# elif oldMsg['msgType'] == 'Picture' \
		# 	or oldMsg['msgType'] == 'Video' \
		# 	or oldMsg['msgType'] == 'Attachment':
		# 	needSendFile = True
		# 	sendMsgPrefix = sendFilePrefixDict[oldMsg['msgType']]
		# 	(oldMsg['msgContent'], msgSend) = RenameFile(oldMsg['msgContent'], msgSend)
		else:
			msgSend += u"Error: Unsupported Type!"

		itchat.send(msgSend, toUserName='filehelper') #将撤回消息的通知以及细节发送到文件助手
		# if needSendFile:
		# 	print(oldMsg['msgContent'])
		# 	itchat.send('%s%s' % (sendMsgPrefix, oldMsg['msgContent']), toUserName='filehelper')
		# 	shutil.move(oldMsg['msgContent'], r"./RevokedMsg/")

		# Clear message dictionary
		msgDict.pop(oldMsgId)
		# ClearTimeOutMsg(msgDict, )

# group texts handling function
@itchat.msg_register([TEXT, RECORDING], isGroupChat=True)
def HandleGroupMsg(self, msg):
	print('%s received a group msg' % self.NickName)

	# initial a group or update nick name of a gorup
	groupID = msg['User']['EncryChatRoomId']
	groupNickName = msg['User']['NickName']
	if groupID not in groupDict.keys():
		groupDict[groupID] = groupCache(groupID, groupNickName)
	elif groupNickName != groupDict[groupID].groupNickName:
		groupDict[groupID].groupNickName = groupNickName

	# add new msg to every previous notify msg
    if msg['Type'] == 'Recording':
        msgContent = msg['Text']
	# elif msg['Type'] == 'Recording':
	# 	msgContent = r"./ReceivedMsg/GroupRecording/" + msg['FileName']
	# 	msg['Text'](msgContent)

	id = groupDict[groupID].addMsg(msg)
	for Smsg in groupDict[groupID].singleMsg:
		if Smsg.msgID == id - 1:
			Smsg.nextText[0] = (msgContent, msg['ActualNickName'], msg['Type'])
		elif Smsg.msgID == id - 2:
			Smsg.nextText[1] = (msgContent, msg['ActualNickName'], msg['Type'])

	# check whether it is a notify message
	if checkGroupNotify(msg, groupID):
		groupDict[groupID].addNotifyMsg(msg)
		print("%s was @ in a group (%s)" % (self.NickName, msg['Text']))

	groupDict[groupID].addPointer()
	# for key in groupDict.keys():
	# 	print(key)

#将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
#没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
def HandleMsg(self, msg):
	print('%s received a msg' % self.NickName)

	# ignore the msg which a user send to himself/herself
	if msg['FromUserName'] == msg['ToUserName']:
		return;
	# it maybe is a robot control message
	if msg['ToUserName'] == 'filehelper':
		robotControl(msg)

	# get localtime and convert it into a user-friendly format coz it will be shown to a user
	mytime = time.localtime()
	msgTimeToUser = mytime.tm_year.__str__() \
                      + "/" + mytime.tm_mon.__str__() \
                      + "/" + mytime.tm_mday.__str__() \
                      + " " + mytime.tm_hour.__str__() \
                      + ":" + mytime.tm_min.__str__() \
                      + ":" + mytime.tm_sec.__str__()

	msgId = msg['MsgId'] # id
	msgTime = msg['CreateTime'] # time
	msgFrom = msg['FromUserName']
	msgTo = msg['ToUserName']
	msgType = msg['Type'] # type
	msgText = None # for plain msg
	msgBin = None # for binary msg (e.g. photo, file, recording...)
	msgUrl = None # a sharing msg has a url

	if msg['Type'] == 'Text':
		msgText = msg['Text']

	# elif msg['Type'] == 'Picture':
	# 	msgContent = r"./ReceivedMsg/Picture/" + msg['FileName']
	# 	msg['Text'](msgContent)

	# elif msg['Type'] == 'Card':
	# 	msgContent = msg['RecommendInfo']['NickName'] + r" 的名片"

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
    #
	# elif msg['Type'] == 'Recording':
	# 	msgContent = r"./ReceivedMsg/Recording/" + msg['FileName']
	# 	msg['Text'](msgContent)
    #
	# elif msg['Type'] == 'Attachment':
	# 	msgContent = r"./ReceivedMsg/Attachment/" + msg['FileName']
	# 	msg['Text'](msgContent)
    #
	# elif msg['Type'] == 'Video':
	# 	msgContent = r"./ReceivedMsg/Video/" + msg['FileName']
	# 	msg['Text'](msgContent)

	elif msg['Type'] == 'Friends':
		msgText = msg['Text']

	elif msg['Type'] == 'Note':
		HandleNote(msg)
		return

	# insert this msg to DB
	msg_obj = Message(msg_id=msgId, msg_type=msgType, msg_time=msgTime, \
						msg_from=msgFrom, msg_to=msgTo, msg_url=msgUrl, \
						msg_text=msgText, msg_bin=msgBin, msg_json=msg)
	msg_obj.save()
    # # clear msg which lasting longer than 2 mins
    # timestamp = time.time()
	# ClearTimeOutMsg(self.msgDict, timestamp)
