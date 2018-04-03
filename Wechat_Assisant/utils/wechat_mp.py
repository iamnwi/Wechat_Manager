import sys, logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Wechat_MP():
    def __init__(self):
      self.app_id = 'wx8a9b7b3c741a2414'
      self.app_secret = '07004aa665d414d3ad0b1abb34ff43b7'
      self.token = '520william'
      self.access_token, self.expire_duration, self.access_token_stamp = self.get_access_token()

    def validate(self, request):
        signature = request.REQUEST.get('signature', '')
        timestamp = request.REQUEST.get('timestamp', '')
        nonce = request.REQUEST.get('nonce',  '')

        tmp_str = hashlib.sha1(''.join(sorted([self.token, timestamp, nonce]))).hexdigest()
        if tmp_str == signature:
            return True
        
        return False

    def get(self, request):
        if self.validate(request):
            return HttpResponse(request.REQUEST.get('echostr', ''))
        raise PermissionDenied

    def get_access_token(self):
        logger.info("get access token")
        params = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret
        }
        host = 'api.weixin.qq.com'
        path = '/cgi-bin/token'
        method = 'GET'

        res = self._send_request(host, path, method, params=params)
        logger.info("access res: %s" % res)
        logger.info("access res[0]: %s, res[1]: %s" % (res[0], res[1]))
        if not res[0]:
            log_error(res[1])
            return False
        if res[1].get('errcode'):
            log_error(res[1].get('errmsg'))
            return False
        return res[1], ,res[2], time.time()

    def send_request(self, host, path, method, port=443, params={}):
        client = httplib.HTTPSConnection(host, port)

        path = '?'.join([path, urllib.urlencode(params)])
        client.request(method, path)

        res = client.getresponse()
        if not res.status == 200:
            return False, res.status

        return True, json.loads(res.read())

    def update_access_token():
        self.access_token, self.expire_duration, self.access_token_stamp = self.get_access_token()
