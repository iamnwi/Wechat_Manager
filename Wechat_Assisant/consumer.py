import json
import logging

from channels.generic.websocket import WebsocketConsumer
from Wechat_Assisant.models import *
from .utils.assisant import Assisant

# mp
from multiprocessing import Process

# Get an instance of a logger
logger = logging.getLogger(__name__)

class WechatConsumer(WebsocketConsumer):
    def ws_login(self, openid):
        logger.info("login request")
        logger.info("get uuid")
        try:
            uuid = Assisant.get_QRuuid()
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
            p = Process(target=Assisant.check_login, args=(uuid, openid, ))
            p.daemon = True
            logger.info("fork a worker process for client(uuid:%s)" % uuid)
            p.start()
        except:
            logger.error("Unknown Exception Occured!")
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
