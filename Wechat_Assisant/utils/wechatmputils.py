import sys, logging, time, requests, json
from Wechat_Assisant.models import WechatMP
from django.conf import settings

# Get an instance of a logger
logger = logging.getLogger(__name__)

def init_mp():
    app_id = settings.MP_APP_ID
    app_secret = settings.MP_APP_SECRET
    mp, created = WechatMP.objects.update_or_create(app_id=app_id, app_secret=app_secret)
    return mp

def validate(request):
    signature = request.REQUEST.get('signature', '')
    timestamp = request.REQUEST.get('timestamp', '')
    nonce = request.REQUEST.get('nonce',  '')

    tmp_str = hashlib.sha1(''.join(sorted([settings.MP_TOKEN, timestamp, nonce]))).hexdigest()
    if tmp_str == signature:
        return True

    return False

def get_access_token(mp_app_id):
    mp = WechatMP.objects.get(app_id=mp_app_id)
    return mp.access_token

def refresh_access_token(mp):
    logger.info("monitoring access token for MP(appid= %s)" % mp.app_id)
    if not mp.access_token:
        update_access_token(mp)
    time = min(time.time()-mp.access_token_stamp, 3600)
    while True:
        sleep(time)
        update_access_token(mp)
        time = 3600

def update_access_token(mp):
    logger.info("update access token for MP(appid= %s)" % mp.app_id)
    params = {
        'grant_type': 'client_credential',
        'appid': mp.app_id,
        'secret': mp.app_secret
    }
    host = 'api.weixin.qq.com'
    path = '/cgi-bin/token'
    method = 'GET'

    # res = send_request(host, path, method, params=params)
    url = 'https://api.weixin.qq.com/cgi-bin/token'
    try:
        res = json.loads(requests.get(url, data=params, verify=False))
        logger.info("access res: %s" % res)
        # logger.info("access res[0]: %s, res[1]: %s" % (res[0], res[1]))
        if 'access_token' in res:
            log_info("mp(app_id=%s) received access_token %s(expire %s)" % (mp.app_id, res['access_token'], res['expires_in']))
            mp.access_token = res['access_token']
            mp.expire_duration = res['expires_in']
            mp.access_token_stamp = time.time()
            mp.save()
            return True
        else:
            log_error("bad response, errcode = %s, errmsg = %s" % (res['errmsg'], res['errmsg']))
    except Exception as e:
        logger.error(e)
    return False

# def send_request(host, path, method, port=443, params={}):
#     client = httplib.HTTPSConnection(host, port)
#
#     path = '?'.join([path, urllib.urlencode(params)])
#     client.request(method, path)
#
#     res = client.getresponse()
#     if not res.status == 200:
#         return False, res.status
#
#     return True, json.loads(res.read())
