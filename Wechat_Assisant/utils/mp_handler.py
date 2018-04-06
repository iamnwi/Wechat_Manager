from werobot import WeRoBot

from django.conf import settings
from .wechatmputils import *
# mp
from multiprocessing import Process

def run_mp():
    # mp = init_mp()
    # p = Process(target=refresh_access_token, args=(mp, ))
    # p.daemon = True
    # p.start()
    # access_token = get_access_token(settings.MP_APP_ID)
    mp_robot = WeRoBot(token=settings.MP_TOKEN)

    @mp_robot.handler
    def hello(message):
        return 'Hello World!'

    return mp_robot

mp_robot = run_mp()
