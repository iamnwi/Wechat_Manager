from werobot import WeRoBot

from django.conf import settings
from .wechatmputils import *

access_token = get_access_token(settings.MP_APP_ID)
mp_robot = WeRoBot(token=access_token)

@mp_robot.handler
def hello(message):
    return 'Hello World!'
