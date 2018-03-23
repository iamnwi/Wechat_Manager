# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse

from Wechat_Assisant.models import *
from utils.assisant import Assisant

import time
import base64

# mp
from multiprocessing import Process

# Create your views here.
def run_assisant(assisant, openid, unionid):
    print("check assisant login status")
    logined = assisant.check_login()
    if logined:
        print("logined! run...")
        assisant.run()

def login(request):
    print("login request")
    p = request.GET;
    openid = p.get('openid')
    unionid = p.get('unionid')
    if openid != None and unionid != None:
        print("get QR")
        assisant = Assisant()
        qr_code = assisant.get_QR()
        response = {}
        response['type'] = 'img'
        response['data'] = base64.b64encode(qr_code.getvalue())
        print("fork")
        p = Process(target=run_assisant, args=(assisant, openid, unionid, ))
        p.daemon = True
        p.start()
    return JsonResponse(response)
