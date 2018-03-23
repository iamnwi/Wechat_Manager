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
def run_assisant(assisant):
    print("check assisant login status")
    print("sleep")
    time.sleep(1)
    print("wake up")
    logined = assisant.check_login()
    if logined:
        print("logined! run...")
        assisant.run()

def login(request):
    print("login request")
    print("get uuid")
    assisant = Assisant()
    uuid = assisant.get_QRuuid()
    response = {}
    response['type'] = 'uuid'
    response['uuid'] = uuid
    print("fork")
    p = Process(target=run_assisant, args=(assisant, ))
    p.daemon = True
    p.start()
    return JsonResponse(response)

def index(request):
    return render(request, 'index.html', {})
