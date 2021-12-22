import logging
import os
import re
import subprocess
from datetime import datetime
from time import sleep
from typing import List

import requests
import vk_api
from ffprobe import FFProbe
from TikTokAPI import TikTokAPI
from vk_api import VkUpload
from vk_api.bot_longpoll import (VkBotEventType, VkBotLongPoll,
                                 VkBotMessageEvent)
from vk_api.utils import get_random_id


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)8s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_tt_video_id(url: str) -> str:
    a = re.findall(r'((@.*\/.*\/)|(\/v\/))([\d]*)', url)
    return a[-1][-1]


def renew_tt_session():
    global tt_session
    tt_session.close()


def download_tt(tt_link) -> str:
    logging.info('download_tt')

    try:
        response = tt_session.get(tt_link)
    except Exception as e:
        logging.info(e)
        renew_tt_session()
        response = tt_session.get(tt_link)

    api = TikTokAPI(cookie=tt_session.cookies)
    cwd = os.getcwd()
    vid = get_tt_video_id(response.url)
    file_path = cwd + '\\' + vid + '.mp4'
    api.downloadVideoById(vid, file_path)
    response.close()

    return file_path


def split_video(video_path: str, part_len=14) -> List[str]:
    ret = []
    metadata = FFProbe(video_path)
    duration_seconds = metadata.video[0].duration_seconds()
    if duration_seconds <= part_len:
        return [video_path]
    if duration_seconds / 8 > part_len:
        return []

    for i in range(int(duration_seconds + part_len / 2) // part_len):
        fname = video_path + f"_{i}_out.mp4"
        command = f"./ffmpeg.exe -i {video_path} " \
                  f" -ss 00:00:{str(part_len * i).zfill(2)} -t 00:00:{str(part_len).zfill(2)} " \
                  f" -c:v libx264 {fname} -y"
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ret.append(fname)
    os.remove(video_path)
    return ret


def delete_tt_video(tt_videos):
    for video in tt_videos:
        try:
            os.remove(video)
            logging.info(f"video {video} deleted")
        except OSError:
            logging.error(f"can't remove {video}")


def post_tt_video(event: VkBotMessageEvent, message):
    """Get tt link and create vk history in chat"""

    logging.info('process_tt_msg')
    peer_id = event.obj.get('peer_id')
    tt_file = download_tt(message)
    tt_videos = split_video(tt_file)
    vk.messages.setActivity(peer_id=peer_id, type="typing")

    try:
        tt_video = uploader.story(tt_videos[0], 'video', group_id=GROUP_ID)
    except Exception as e:
        logging.error("can't upload story\n")
        return e

    data = tt_video.json()
    attstr = f"story{data['response']['story']['owner_id']}_{data['response']['story']['id']}"

    try:
        vk.messages.send(peer_id=peer_id,
                         attachment=attstr,
                         random_id=get_random_id())
    except Exception as e:
        logging.error("can't send vk message\n")
        delete_tt_video(tt_video)
        return e

    for video in tt_videos[1:]:
        sleep(0.5)
        try:
            uploader.story(video, 'video', group_id=GROUP_ID)
        except Exception as e:
            logging.error("can't upload story\n")
            delete_tt_video(tt_video)
            return e


def renew_vk_logpoll():
    global _vk_session
    global vk_session
    global longpoll
    global GROUP_ID

    _vk_session.close()
    vk_session = vk_api.VkApi(token=BOT_TOKEN, session=_vk_session)
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)


def find_tt_link_in_message(event, message):
    for tiktok_url in TIKTOK_URLS:
        if message.find(tiktok_url) != -1:
            if sender in users:
                if (datetime.now() - users[sender]).seconds < 20:
                    continue
            users[sender] = datetime.now()
            post_tt_video(event, message)


if __name__ == "__main__":
    GROUP_ID = int(os.getenv("GROUP_ID"))
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    TIKTOK_URLS = ['https://vm.tiktok.com', 'https://www.tiktok.com']
    users = {}

    tt_session = requests.sessions.Session()
    _vk_session = requests.sessions.Session()

    vk_session = vk_api.VkApi(token=BOT_TOKEN, session=_vk_session)
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    vk = vk_session.get_api()
    uploader = VkUpload(vk)

    while True:
        try:
            logging.info('start listening')
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    peer_id = event.obj.get('peer_id')
                    message: str = event.obj.get('text')
                    sender = event.obj.get('from_id')

                    find_tt_link_in_message(event, message)

        except requests.exceptions.ReadTimeout:
            logging.error('ReadTimeout')
        except Exception as e:
            logging.error(e)
            renew_vk_logpoll()
            renew_tt_session()
