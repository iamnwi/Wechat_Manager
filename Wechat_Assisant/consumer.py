from channels.generic.websocket import WebsocketConsumer
import json

from Wechat_Assisant.models import *
from .utils.assisant import Assisant

# mp
from multiprocessing import Process

class WechatConsumer(WebsocketConsumer):
    def ws_login(self):
        print("login request")
        print("get uuid")
        assisant = Assisant()
        uuid = assisant.get_QRuuid()
        self.send(text_data=json.dumps({
            'type': 'uuid',
            'uuid': uuid
        }))
        p = Process(target=run_assisant, args=(assisant, ))
        p.daemon = True
        print("fork")
        p.start()

    def connect(self):
        self.accept()
        self.ws_login()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        pass
        # text_data_json = json.loads(text_data)
        # message = text_data_json['message']
        #
        # self.send(text_data=json.dumps({
        #     'message': message
        # }))

def run_assisant(assisant):
    print("check assisant login status")
    logined = assisant.check_login()
    if logined:
        print("logined! run...")
        assisant.run()
