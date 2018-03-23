# -*- coding:utf8 -*-

# use for the notify msg(@someone) in groups,
# recording the msgs before and after the notify msg
class msgCache:
	def __init__(self, text, author, id):
		self.text = text
		self.user = author
		self.preText = [("", "", ""), ("", "", "")]
		self.nextText = [("", "", ""), ("", "", "")]
		self.msgID = id

	def addPreText(self, preText1, preText2):
		self.preText[0] = preText1
		self.preText[1] = preText2

# group msg cache
# using recurrent array
class groupCache:
	def __init__(self, groupID, groupNickName):
		self.cacheList = [('', '', ''), ('', '', ''), ('', '', ''), ('', '', ''), ('', '', '')]
		self.pointer = 0
		self.groupID = groupID
		self.singleMsg = list()
		self.groupMsgID = 0
		self.groupNickName = groupNickName
	def addMsg(self, msg):
		if msg['Type'] == 'Recording':
			msgContent = r"./ReceivedMsg/GroupRecording/" + msg['FileName']
			msg['Text'](msgContent)
		else:
			msgContent = msg['Text']
		self.cacheList[self.pointer] = (msgContent, msg['ActualNickName'], msg['Type'])
		return self.groupMsgID
	def addPointer(self):
		self.pointer = (self.pointer + 1) % 5
		self.groupMsgID += 1
	def addNotifyMsg(self, msg):
		notifyMsg = msgCache(msg['Content'], msg['ActualNickName'], self.groupMsgID)
		preText1 = self.cacheList[(self.pointer - 2 + 5) % 5]
		preText2 = self.cacheList[(self.pointer - 1 + 5) % 5]
		notifyMsg.addPreText(preText1, preText2)
		self.singleMsg.append(notifyMsg)
