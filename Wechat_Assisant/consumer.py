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
        assisant = Assisant(openid)
        logger.info("get uuid")
        try:
            uuid = assisant.get_QRuuid()
            logger.info("got uuid:%s" % uuid)
            self.send(text_data=json.dumps({
                'type': 'uuid',
                'uuid': uuid
            }))
            p = Process(target=run_assisant, args=(assisant, ))
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

def run_assisant(assisant):
    logger.info("check login status of client(uuid:%s)" % assisant.uuid)
    logined = assisant.check_login()
    if logined:
        logger.info("client(uuid:%s) logined! run..." % assisant.uuid)
        assisant.run()
