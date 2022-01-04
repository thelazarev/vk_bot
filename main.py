import logging
import os

import requests
import vk_api
from vk_api import VkUpload
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from utils.commands import Invoker


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)8s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def renew_tt_session():
    global tt_session
    tt_session.close()


def renew_vk_logpoll():
    global _vk_session
    global vk_session
    global longpoll
    global GROUP_ID

    _vk_session.close()
    vk_session = vk_api.VkApi(token=BOT_TOKEN, session=_vk_session)
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)


if __name__ == "__main__":
    GROUP_ID = int(os.getenv("GROUP_ID"))
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    tt_session = requests.sessions.Session()
    _vk_session = requests.sessions.Session()

    vk_session = vk_api.VkApi(token=BOT_TOKEN, session=_vk_session)
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    vk = vk_session.get_api()
    uploader = VkUpload(vk)

    invoker = Invoker(vk, uploader, GROUP_ID)

    while True:
        try:
            logging.info('start listening')
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    invoker.parse_vk_event(event)

        except requests.exceptions.ReadTimeout:
            logging.error('ReadTimeout')
        except Exception as e:
            logging.error(e)
            renew_vk_logpoll()
            renew_tt_session()
