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

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    return render(request, 'index.html', {})

def mp(request):
    data = request.GET
    if not data:
        return HttpResponse("invalid request")

    signature = data.get('signature')
    timestamp = data.get('timestamp')
    nonce = data.get('nonce')
    echostr = data.get('echostr')
    token = "520william"

    arg_list = [token, timestamp, nonce]
    arg_list.sort()
    sha1 = hashlib.sha1()
    map(sha1.update, arg_list)
    hashcode = sha1.hexdigest()
    logger.info("mp/GET func: hashcode, signature: " % (hashcode, signature))
    if hashcode == signature:
        return HttpResponse(echostr)
    else:
        return "error"
