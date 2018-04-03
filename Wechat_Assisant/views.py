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

# wechat_mp = Wechat_MP()
# p = Process(target=check_access_token, args=(wechat_mp, ))
# p.daemon = True
# logger.info("fork a access token checking process")
# p.start()

def check_access_token(wechat_mp):
    logger.info("check access token")
    if time.time() - wechat_mp.access_token_stamp > wechat_mp.expire_duration:
        wechat_mp.update_access_token()
    else:
        logger.info("access token still work, sleep 10s")
        sleep(10)

# Create your views here.
def index(request):
    return render(request, 'index.html', {})
