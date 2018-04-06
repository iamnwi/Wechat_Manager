# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse

from Wechat_Assisant.models import *
from .utils.assisant import Assisant
from .utils.wechatmputils import *

import time
import base64
import hashlib
import logging

# mp
from multiprocessing import Process

# Get an instance of a logger
logger = logging.getLogger(__name__)

def push(openid):
    wc = get_wc(openid=openid)
    if wc:
        assistant = Assisant(openid)
        try:
            uuid = assistant.login_returned_client(wc)
        except:
            logger.error("Unknown Exception Occured During Getting Push Login uuid!")
            return False
        p = Process(target=run_returned_assistant, args=(assistant, ))
        p.daemon = True
        logger.info("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
        p.start()
        return True
    logger.info("cannot find cookies of client(openid:%s)" % (openid))
    return False

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
        status = push(data['openid'])
        if status:
            return HttpResponse('200')
        else:
            return HttpResponse('500')
    return HttpResponse('arg errors')

def wxmp(requests):
    if validate(requests):
        return HttpResponse(requests.GET.get('echostr', ''))
    return HttpResponse('ERROR')
