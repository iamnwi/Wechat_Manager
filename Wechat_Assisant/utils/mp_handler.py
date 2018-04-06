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
    mp_robot.config["APP_ID"] = "wx8a9b7b3c741a2414"
    mp_robot.config["APP_SECRET"] = "07004aa665d414d3ad0b1abb34ff43b7"

    @mp_robot.handler
    def hello(message):
        return 'Hello World!'

    return mp_robot

mp_robot = run_mp()
#mp_robot = WeRoBot(token='520william')
#mp_robot.config["APP_ID"] = "wx8a9b7b3c741a2414"
#mp_robot.config["APP_SECRET"] = "07004aa665d414d3ad0b1abb34ff43b7"


#@mp_robot.handler
#def hello(message):
#    return 'Hello World!'
