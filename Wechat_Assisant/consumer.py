import json
import logging
import traceback

from channels.generic.websocket import WebsocketConsumer
from Wechat_Assisant.models import *
from .utils.assisant import Assisant

# mp
from multiprocessing import Process
# mt
import threading

# Get an instance of a logger
logger = logging.getLogger(__name__)

class WechatConsumer(WebsocketConsumer):
    def ws_login(self, openid):
        logger.info("login request")
        logger.info("get uuid")
        try:
            uuid = Assisant.get_QRuuid(openid)
            logger.info("got uuid:%s" % uuid)
            # initial login status
            wc = get_wc(openid=openid)
            if wc:
                wc.login_status = 0
            else:
                wc = WechatClient(openid=openid)
            wc.save()
            # send uuid to web client
            logger.info("send uuid(%s) to web client" % uuid)
            self.send(text_data=json.dumps({
                'type': 'uuid',
                'uuid': uuid
            }))
            # initial login status
            wc = get_wc(openid=openid)
            if wc:
                wc.login_status = 0
            else:
                close_old_connections()
                wc = WechatClient(openid=openid)
            wc.save()
            # check login status and run itchat if client login successfully
            logined = Assisant.check_login(uuid, openid)
            if logined:
                t = threading.Thread(target=Assisant.run_assisant, args=(uuid, openid,))
                t.daemon = True
                print("fork a worker thread for client(openid:%s, uuid:%s)" % (openid, uuid))
                t.start()
            # p = Process(target=Assisant.check_login, args=(uuid, openid, ))
            # p.daemon = True
            # logger.info("fork a worker process for client(uuid:%s)" % uuid)
            # p.start()
        except Exception as e:
            logger.error("Unknown Exception Occured!")
            traceback.print_exc()
            self.send(text_data=json.dumps({
                'type': 'error',
                'detail': 'Connection Error'
            }))

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        data = json.loads(text_data)
        if 'type' in data and data['type']=='login':
            logger.info("receive login wb, openid=%s" % data['openid'])
            self.ws_login(data['openid'])
