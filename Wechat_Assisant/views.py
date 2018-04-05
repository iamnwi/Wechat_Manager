# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse

from Wechat_Assisant.models import *
from .utils.assisant import Assisant

import time
import base64
import hashlib
import logging

# mp
from multiprocessing import Process

# wehcat-mp utils
from .utils.wechatmputils import *

# Get an instance of a logger
logger = logging.getLogger(__name__)

def run_mp():
    mp = init_mp()
    p = Process(target=refresh_access_token, args=(mp, ))
    p.daemon = True
    p.start()

run_mp()

def run_returned_assistant(assistant):
    logger.info("check login status of client(uuid:%s)" % assistant.uuid)
    logined = assistant.check_login()
    if logined:
        logger.info("client(uuid:%s) logined! run..." % assistant.uuid)
        assistant.run()

# Create your views here.
def index(request):
    return render(request, 'index.html', {})

def pushlogin(request):
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    if 'openid' in data:
        openid = data['openid']
        wc = get_wc(openid=openid)
        if wc:
            assistant = Assisant(openid)
            try:
                uuid = assistant.login_returned_client(wc)
            except:
                logger.error("Unknown Exception Occured During Getting Push Login uuid!")
                return HttpResponse('unknown errors')
            p = Process(target=run_returned_assistant, args=(assistant, ))
            p.daemon = True
            logger.info("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
            p.start()
            return HttpResponse('200')

    return HttpResponse('arg errors')
