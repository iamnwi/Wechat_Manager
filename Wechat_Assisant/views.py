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
import traceback
# import signal
import _thread

# mp
from multiprocessing import Process
# process_ls = []

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
        _thread.start_new_thread(run_returned_assistant, (openid, uuid, ))
        #p = Process(target=run_returned_assistant, args=(openid, uuid,))
        #p.daemon = True
        #print("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
        #p.start()
        return True
    print("cannot find cookies of client(openid:%s)" % (openid))
    return False

def run_returned_assistant(openid, uuid):
    print("check login status of client(uuid:%s)" % uuid)
    logined = Assisant.check_login(uuid, openid)
    if logined:
        print("client(uuid:%s, openid:%s) logined! run..." % (uuid, openid))
        Assisant.run_assisant(uuid, openid)

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
        ins.send(settings.LOGOUT_BY_ADMIN_MSG, toUserName='filehelper')
        print("sent and now logout")
        ins.logout()

# def interrupt_handler(signal, frame):
#         print('Admin pressed Ctrl+C! Killing all processes...')
#
#         print('Done! Exit.')
#         sys.exit(0)

# signal.signal(signal.SIGINT, interrupt_handler)

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
            _thread.start_new_thread(Assisant.run_assisant, (uuid, openid, ))
            #p = Process(target=Assisant.run_assisant, args=(uuid, openid,))
            #p.daemon = True
            #print("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
            #p.start()
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
        # # initial login status
        # wc = get_wc(openid=openid)
        # if wc:
        #     wc.login_status = 0
        # else:
        #     wc = WechatClient(openid=openid)
        # wc.save()
        # fork a process to keep checking the login status
        # p = Process(target=Assisant.check_login, args=(uuid, openid, ))
        # p.daemon = True
        # print("fork a worker process for client(openid:%s, uuid:%s)" % (openid, uuid))
        # p.start()
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

    # if 'uuid' in data and 'openid' in data:
    #     uuid = data['uuid']
    #     openid = data['openid']
    #     status = Assisant.check_login_once(uuid)
    #     if status == '200':
    #         print("[views.loginstatus][status %s] client(openid=%s, uuid=%s) login successfully" % (status, openid, uuid))
    #         return JsonResponse({'code': status})
    #     elif status == '201':
    #         print("[views.loginstatus][status %s] waiting client(openid=%s, uuid=%s) to confirm on phone" % (status, openid, uuid))
    #         return JsonResponse({'code': status})
    #     else:
    #         print("[views.loginstatus][status %s] client(openid=%s, uuid=%s) qrcode is timeout" % (status, openid, uuid))
    #         return JsonResponse({'code': status})
    # else:
    #     return JsonResponse({'code': '400'})

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
