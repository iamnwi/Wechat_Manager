# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings

from Wechat_Assisant.models import *
from .utils.assisant import Assisant
from .utils.wechatmputils import *
from .utils.constant import Constant

import time
import base64
import hashlib
import traceback

# mp
from multiprocessing import Process
# mt
import threading

# Get an instance of a logger
import logging
logger = logging.getLogger(__name__)

def push(openid):
    wc = get_wc(openid=openid)
    if wc:
        try:
            uuid = Assisant.login_returned_client(wc, openid)
        except Exception as e:
            print("Unknown Exception Occured During Getting Push Login uuid!")
            traceback.print_exc()
            return False
        t = threading.Thread(target=Assisant.run_returned_client, args=(openid, uuid,))
        t.daemon = True
        print("fork a worker thread for client(openid:%s, uuid:%s)" % (openid, uuid))
        t.start()
        return True
    print("cannot find cookies of client(openid:%s)" % (openid))
    return False

def kick():
    print("admin requested to log out all online clients. Kicking...")
    if Assisant.instance_dict is None:
        print("instance dict is EMPTY!")
    print(len(Assisant.instance_dict))
    for openid in list(Assisant.instance_dict.keys()):
        assistant = Assisant.instance_dict[openid]
        ins = assistant.itchat_ins
        uin = (ins.search_friends())['Uin']
        print("send logout-by-admin msg to client(openid=%s, uin=%s) and logout" % (openid, uin))
        ins.send(Constant.LOGOUT_BY_ADMIN_MSG, toUserName='filehelper')
        print("sent and now logout")
        ins.logout()

# Create your views here.
def index(request):
    return render(request, 'index.html', {})

def extend(request, sid=None):
    if sid is None:
        return HttpResponse('400')

    sid = int(sid) - 10000
    close_old_connections()
    url_qs = ShortUrl.objects.filter(id=sid)
    if url_qs.exists():
        openid = url_qs.get(id=sid).openid
        url = "http://%s/wm/index?openid=%s" % (settings.WECHAT_MANAGER_SERVER, openid)
        return redirect(url)
    else:
        return HttpResponse('400')

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

    if 'uuid' in data and 'openid' in data:
        openid = data['openid']
        uuid = data['uuid']
        # initial login status
        wc = get_wc(openid=openid)
        if wc:
            wc.login_status = 0
        else:
            close_old_connections()
            wc = WechatClient(openid=openid)
        wc.save()
        logined = Assisant.check_login(uuid, openid)
        if logined:
            t = threading.Thread(target=Assisant.run_assisant, args=(uuid, openid,))
            t.daemon = True
            print("fork a worker thread for client(openid:%s, uuid:%s)" % (openid, uuid))
            t.start()
            return JsonResponse({'code': '200'})
        return JsonResponse({'code': '500'})
    else:
        return JsonResponse({'code': '400'})

def getuuid(request):
    print("get uuid request")
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    openid = data['openid']
    try:
        uuid = Assisant.get_QRuuid(openid)
        print("got uuid:%s" % uuid)
        return JsonResponse({
            'code': '200',
            'type': 'uuid',
            'uuid': uuid
        })
    except Exception as e:
        print("Unknown Exception Occured! %s" % e)
        return JsonResponse({
            'code': '500',
            'type': 'error',
            'detail': 'Connection Error'
        })

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
