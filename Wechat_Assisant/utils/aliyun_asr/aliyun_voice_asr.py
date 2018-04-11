# -*- coding:utf8 -*-
import requests
import email.utils
import json
from django.conf import settings

import os;

os.environ["JAVA_HOME"] = settings.JAVA_HOME

import jnius_config

jnius_config.set_classpath('.', settings.JAVA_CLASS_PATH)

from jnius import autoclass

def sendAsrPost(audio_path, audio_format, sample_rate, url, ak_id, ak_secret):
    if url is None:
        url = "http://nlsapi.aliyun.com/recognize?model=customer-service-8k"

    method = 'POST'
    accept = 'application/json'
    content_type = "audio/%s;samplerate=%s" % (audio_format, sample_rate)
    date = email.utils.formatdate(usegmt=True)
    authHeader = generate_auth_header(audio_path, audio_format, sample_rate, ak_id, ak_secret, date)

    print(authHeader)

    audio_f_len = 0
    with open(audio_path, "rb") as f:
        audio_data = f.read()
        audio_f_len = len(audio_data)

    headers = { 'accept': accept,
                'content-type': content_type,
                'date': date,
                'Authorization': authHeader,
                'Content-Length': str(audio_f_len)}
    res = requests.post(url, data=audio_data, headers=headers)
    return res

def generate_auth_header(audio_path, audio_format, sample_rate, ak_id, ak_secret, date):
    JString = autoclass('java.lang.String')
    HttpUtil = autoclass('HttpUtil')
    audio_path = JString(audio_path)
    audio_format = JString(audio_format)
    sample_rate = JString(sample_rate)
    ak_id = JString(ak_id)
    ak_secret = JString(ak_secret)
    date = JString(date)
    auth = HttpUtil.EncryptAuthHeader(audio_path, audio_format, sample_rate, ak_id, ak_secret, date)
    return auth
