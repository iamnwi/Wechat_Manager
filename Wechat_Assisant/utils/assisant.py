# -*- coding:utf8 -*-
import re
import sys
import time
import os
import shutil
import requests
import json

# my itchat
from site_package import itchat
from site_package.itchat.content import *
from cache import *
from assisantutils import *
from Wechat_Assisant.models import *

class Assisant():
    def __init__(self):
        self.uuid = None

    def init_client(self):
        itchat.set_login()
        uin = (itchat.search_friends())['Uin']
        user_name = (itchat.search_friends())['UserName']
        nick_name = (itchat.search_friends())['NickName']
        print("login info: uin=%s, NickName=%s" % (uin, nick_name));
        client_qs = WechatClient.objects.filter(uin=uin)
        if client_qs.count() == 0:
            wc = WechatClient(uin=uin, user_name=user_name, nick_name=nick_name, online=True)
            wc.save()
        elif client_qs.count() == 1:
            wc = client_qs.get(uin=uin)
            wc.user_name = user_name
            wc.nick_name = nick_name
            wc.online = True
            wc.save()

    def run(self):
        self.init_client()
        itchat.run()

    def get_QR(self):
        print('Getting uuid of QR code.')
        self.uuid = itchat.get_QRuuid()
        while not self.uuid:
            self.uuid = itchat.get_QRuuid()
            time.sleep(1)
        print('Downloading QR code.')
        qrStorage = itchat.get_QR(uuid=self.uuid)
        return qrStorage

    def check_login(self):
        print('checking login status')
        isLoggedIn = False
        while not isLoggedIn:
            status = itchat.check_login(self.uuid)
            if status == '200':
                isLoggedIn = True
            elif status == '201':
                if isLoggedIn is not None:
                    print('Please press confirm on your phone.')
                    isLoggedIn = None
            else:
                break
        if isLoggedIn:
            return True
        else:
            print('Log in time out, reloading QR code.')
            return False

    # #收到note类消息，判断是不是撤回并进行相应操作
    # def HandleNote(self, msg):
    # 	print("%s received a note msg" % self.NickName)
    #
    # 	# if not os.path.exists("./RevokedMsg/"):
    # 	# 	os.mkdir("./RevokedMsg/")
    #
    # 	print(msg['Content'])
    # 	if re.search(r"\<replacemsg\>\<\!\[CDATA\[.*撤回了一条消息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
    # 		or re.search(r"\<replacemsg\>\<\!\[CDATA\[.*回收一則訊息\]\]\>\<\/replacemsg\>", msg['Content'].encode('utf8')) != None \
    # 		or re.search(r"\<replacemsg\>\<\!\[CDATA\[.*recalled a message\.\]\]\>\<\/replacemsg\>", msg['Content']) != None:
    # 		print("Revoke a message")
    # 		oldMsgId = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
    # 		oldMsg = msgDict.get(oldMsgId, {})
    # 		msgSend = u"您的好友：" \
    # 				   + oldMsg.get('msgFrom') \
    # 				   + u"  在 [" + oldMsg.get('msgTimeToUser') \
    # 				   + u"], 撤回了一条 [" + oldMsg['msgType'] + u"] 消息, 内容如下:"
    #
    # 		needSendFile = False
    # 		print(oldMsg['msgType'])
    # 		if oldMsg['msgType'] == "Text":
    # 			msgSend += oldMsg['msgContent']
    # 		elif oldMsg['msgType'] == "Sharing":
    # 			msgSend += u", 链接: " + oldMsg.get('msgUrl', None)
    # 		# elif oldMsg['msgType'] == 'Recording':
    # 		# 	needSendFile = True
    # 		# 	audioFileName = oldMsg['msgContent'].split('/')[-1].split('.')[0]
    # 		# 	result = audio2text(convert(oldMsg['msgContent'], "./RevokedMsg/converted/"+audioFileName+".wav"))
    # 		# 	print("ASR result:" + result)
    # 		# 	msgSend += u'\n' + result
    # 		# 	msgSend += u"\n 以上语音转文字后的结果，如有需要请查听 ./RevokedMsg/" + audioFileName
    # 		# 	sendMsgPrefix = sendFilePrefixDict['Attachment']
    # 		# elif oldMsg['msgType'] == 'Picture' \
    # 		# 	or oldMsg['msgType'] == 'Video' \
    # 		# 	or oldMsg['msgType'] == 'Attachment':
    # 		# 	needSendFile = True
    # 		# 	sendMsgPrefix = sendFilePrefixDict[oldMsg['msgType']]
    # 		# 	(oldMsg['msgContent'], msgSend) = RenameFile(oldMsg['msgContent'], msgSend)
    # 		else:
    # 			msgSend += u"Error: Unsupported Type!"
    #
    # 		itchat.send(msgSend, toUserName='filehelper') #将撤回消息的通知以及细节发送到文件助手
    # 		# if needSendFile:
    # 		# 	print(oldMsg['msgContent'])
    # 		# 	itchat.send('%s%s' % (sendMsgPrefix, oldMsg['msgContent']), toUserName='filehelper')
    # 		# 	shutil.move(oldMsg['msgContent'], r"./RevokedMsg/")
    #
    # 		# Clear message dictionary
    # 		msgDict.pop(oldMsgId)
    # 		# ClearTimeOutMsg(msgDict, )
    #
    # # group texts handling function
    # @itchat.msg_register([TEXT, RECORDING], isGroupChat=True)
    # def HandleGroupMsg(self, msg):
    # 	print('%s received a group msg' % self.NickName)
    #
    # 	# initial a group or update nick name of a gorup
    # 	groupID = msg['User']['EncryChatRoomId']
    # 	groupNickName = msg['User']['NickName']
    # 	if groupID not in groupDict.keys():
    # 		groupDict[groupID] = groupCache(groupID, groupNickName)
    # 	elif groupNickName != groupDict[groupID].groupNickName:
    # 		groupDict[groupID].groupNickName = groupNickName
    #
    # 	# add new msg to every previous notify msg
    #     if msg['Type'] == 'Recording':
    #         msgContent = msg['Text']
    # 	# elif msg['Type'] == 'Recording':
    # 	# 	msgContent = r"./ReceivedMsg/GroupRecording/" + msg['FileName']
    # 	# 	msg['Text'](msgContent)
    #
    # 	id = groupDict[groupID].addMsg(msg)
    # 	for Smsg in groupDict[groupID].singleMsg:
    # 		if Smsg.msgID == id - 1:
    # 			Smsg.nextText[0] = (msgContent, msg['ActualNickName'], msg['Type'])
    # 		elif Smsg.msgID == id - 2:
    # 			Smsg.nextText[1] = (msgContent, msg['ActualNickName'], msg['Type'])
    #
    # 	# check whether it is a notify message
    # 	if checkGroupNotify(msg, groupID):
    # 		groupDict[groupID].addNotifyMsg(msg)
    # 		print("%s was @ in a group (%s)" % (self.NickName, msg['Text']))
    #
    # 	groupDict[groupID].addPointer()
    # 	# for key in groupDict.keys():
    # 	# 	print(key)
    #
    # #将接收到的消息存放在字典中，当接收到新消息时对字典中超时的消息进行清理
    # #没有注册note（通知类）消息，通知类消息一般为：红包 转账 消息撤回提醒等，不具有撤回功能
    # @itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS, NOTE])
    # def HandleMsg(self, msg):
    # 	print('%s received a msg' % self.NickName)
    #
    # 	if msg['FromUserName'] == self.UserName:
    # 		# maybe it is a control message
    # 		if msg['ToUserName'] == 'filehelper':
    # 			robotControl(msg)
    # 		# 忽略自己給自己發的消息
    # 		else:
    # 			return
    #
    # 	mytime = time.localtime()  # 这儿获取的是本地时间
    # 	#获取用于展示给用户看的时间 2017/03/03 13:23:53
    # 	msgTimeToUser = mytime.tm_year.__str__() \
    #                       + "/" + mytime.tm_mon.__str__() \
    #                       + "/" + mytime.tm_mday.__str__() \
    #                       + " " + mytime.tm_hour.__str__() \
    #                       + ":" + mytime.tm_min.__str__() \
    #                       + ":" + mytime.tm_sec.__str__()
    #
    # 	msgId = msg['MsgId'] #消息ID
    # 	msgTime = msg['CreateTime'] #消息时间
    # 	msgFrom = itchat.search_friends(userName=msg['FromUserName'])['NickName'] #消息发送人昵称
    # 	msgType = msg['Type'] #消息类型
    # 	msgContent = None #根据消息类型不同，消息内容不同
    # 	msgUrl = None #分享类消息有url
    #
    # 	if msg['Type'] == 'Text':
    # 		msgContent = msg['Text']
    # 		#msg.user.send(msg.text)
    #
    # 	# elif msg['Type'] == 'Picture':
    # 	# 	msgContent = r"./ReceivedMsg/Picture/" + msg['FileName']
    # 	# 	msg['Text'](msgContent)
    #
    # 	elif msg['Type'] == 'Card':
    # 		msgContent = msg['RecommendInfo']['NickName'] + r" 的名片"
    #
    # 	elif msg['Type'] == 'Map':
    # 		x, y, location = \
    # 			re.search("<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
    # 		if location is None:
    # 			msgContent = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
    # 		else:
    # 			msg_content = r"" + location
    #
    # 	# elif msg['Type'] == 'Sharing':
    # 	# 	msgContent = msg['Text']
    # 	# 	msgUrl = msg['Url']
    #     #
    # 	# elif msg['Type'] == 'Recording':
    # 	# 	msgContent = r"./ReceivedMsg/Recording/" + msg['FileName']
    # 	# 	msg['Text'](msgContent)
    #     #
    # 	# elif msg['Type'] == 'Attachment':
    # 	# 	msgContent = r"./ReceivedMsg/Attachment/" + msg['FileName']
    # 	# 	msg['Text'](msgContent)
    #     #
    # 	# elif msg['Type'] == 'Video':
    # 	# 	msgContent = r"./ReceivedMsg/Video/" + msg['FileName']
    # 	# 	msg['Text'](msgContent)
    #
    # 	elif msg['Type'] == 'Friends':
    # 		msgContent = msg['Text']
    #
    # 	elif msg['Type'] == 'Note':
    # 		HandleNote(msg)
    # 		return
    #
    #     #更新字典
    #     # {msg_id:(msg_from,msg_time,msg_time_touser,msg_type,msg_content,msg_url)}
    # 	self.msgDict.update(
    # 		{msgId: {"msgFrom": msgFrom, "msgTime": msgTime, "msgTimeToUser": msgTimeToUser, "msgType": msgType,
    #                   "msgContent": msgContent, "msgUrl": msgUrl}})
    # 	# oldMsg = self.msgDict.get(msgId, {})
    #     #清理字典
    #     timestamp = time.time()
    # 	ClearTimeOutMsg(self.msgDict, timestamp)
