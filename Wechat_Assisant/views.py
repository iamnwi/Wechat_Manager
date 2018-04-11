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
logger = logging.getLogger('web-logger')

def push(openid):
    wc = get_wc(openid=openid)
    if wc:
        assistant = Assisant(openid)
        try:
            uuid = assistant.login_returned_client(wc)
        except:
            print("Unknown Exception Occured During Getting Push Login uuid!")
            return False
        p = Process(target=run_returned_assistant, args=(assistant, ))
        p.daemon = True
        print("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
        p.start()
        return True
    print("cannot find cookies of client(openid:%s)" % (openid))
    return False

def run_returned_assistant(assistant):
    print("check login status of client(uuid:%s)" % assistant.uuid)
    logined = assistant.check_login(assistant.uuid, assistant.openid)
    if logined:
        print("client(uuid:%s) logined! run..." % assistant.uuid)
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

def wxmp(request):
    if validate(request):
        return HttpResponse(request.GET.get('echostr', ''))
    return HttpResponse('ERROR')

def login(request):
    print("login request")
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    openid = data['openid']
    try:
        error = False
        uuid = Assisant.get_QRuuid()
        print("got uuid:%s" % uuid)
        # initial login status
        wc = get_wc(openid=openid)
        if wc:
            wc.login_status = 0
        else:
            wc = WechatClient(openid=openid)
        wc.save()
        # fork a process to keep checking the login status
        p = Process(target=Assisant.check_login, args=(uuid, openid, ))
        p.daemon = True
        #print("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
        #p.start()
        return JsonResponse({
            'type': 'uuid',
            'uuid': uuid
        })
    except Exception as e:
        error = True
        print("Unknown Exception Occured! %s" % e)
        return JsonResponse({
            'type': 'error',
            'detail': 'Connection Error'
        })
    finally:
        if not error:
            p = Process(target=Assisant.check_login, args=(uuid, openid, ))
            p.daemon = True

def loginstatus(request):
    print("loginstatus request")
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    if 'openid' in data:
        openid = data['openid']
        wc = get_wc(openid=openid)
        if wc:
            status = wc.login_status
            if status == '200':
                print("client(openid = %s) login successfully" % openid)
                return JsonResponse({'code': status})
            elif status == '201':
                print("waiting client(openid = %s) to confirm on phone" % openid)
                return JsonResponse({'code': status})
            elif status == '408':
                print("client(openid = %s) qrcode is timeout" % openid)
                return JsonResponse({'code': status})
            else:
                print("not yet receive client's(openid = %s) login status" % openid)
                return JsonResponse({'code': status})
        else:
            print("No records related to openid = %s" % openid)
            return JsonResponse({'code': '400'})
    else:
        return JsonResponse({'code': '400'})
