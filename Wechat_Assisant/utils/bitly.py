import requests
from django.conf import settings

def shorten(uri):
    query_params = {
        'access_token': settings.BITLY_ACCESS_TOKEN,
        'longUrl': uri
    }
    endpoint = 'https://api-ssl.bitly.com/v3/shorten'
    response = requests.get(endpoint, params=query_params, verify=False)

    data = response.json()
    if not data['status_code'] == 200:
        logger.error("Unexpected status_code: {} in bitly response. {}".format(data['status_code'], response.text))

    return data['data']['url']
