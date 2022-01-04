import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import List

import urllib3
from ffprobe import FFProbe
from vk_api.bot_longpoll import VkBotMessageEvent
from vk_api.utils import get_random_id


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)8s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def download_data(uri):
    UA_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " + \
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"

    http = urllib3.PoolManager(10, headers={'user-agent': UA_CHROME})
    logging.info("getting url data...")

    r1 = http.urlopen('GET', uri) or None
    return r1


def video_url_parse(tt_page_content):
    download_address = re.compile('downloadAddr":"(.*)","shareCover')
    return download_address.search(tt_page_content.data.decode('unicode-escape')).group(1)


def download_tt_video(url, name):
    tt_page_content = download_data(url)
    tt_video_link = video_url_parse(tt_page_content)
    tt_video = download_data(tt_video_link)

    tmp_directory = f'{Path(__file__).resolve().parent.parent}/tmp'

    with open(f'{tmp_directory}/{name}', "wb") as f:
        f.write(tt_video.data)

    return f'{tmp_directory}/{name}'


def get_tt_video_id(url: str) -> str:
    a = re.findall(r'((@.*\/.*\/)|(\/v\/))([\d]*)', url)
    return a[-1][-1]


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
        command = f"ffmpeg -i {video_path}" \
                  f" -ss 00:00:{str(part_len * i).zfill(2)} -t 00:00:{str(part_len).zfill(2)}" \
                  f" -c:v libx264 {fname} -y"
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        ret.append(fname)
    os.remove(video_path)
    return ret


def delete_split_tt_videos(tt_videos):
    for video in tt_videos:
        try:
            os.remove(video)
            logging.info(f"video {video} deleted")
        except OSError:
            logging.error(f"can't remove {video}")


def post_tt_video(vk, uploader, group_id, event: VkBotMessageEvent):
    """Get tt link and create vk history in chat"""

    logging.info('process_tt_msg')
    peer_id = event.obj.get('peer_id')
    tt_file = download_tt_video(event.obj.get('text'), f'{str(int(datetime.now().timestamp()))}.mp4')
    tt_videos = split_video(tt_file)
    vk.messages.setActivity(peer_id=peer_id, type="typing")

    try:
        tt_video = uploader.story(tt_videos[0], 'video', group_id=group_id)
    except Exception as e:
        logging.error("can't upload story\n")
        delete_split_tt_videos(tt_videos)
        return e

    data = tt_video.json()
    attstr = f"story{data['response']['story']['owner_id']}_{data['response']['story']['id']}"

    try:
        vk.messages.send(peer_id=peer_id,
                         attachment=attstr,
                         random_id=get_random_id())
    except Exception as e:
        logging.error("can't send vk message\n")
        delete_split_tt_videos(tt_videos)
        return e

    for video in tt_videos[1:]:
        sleep(0.5)
        try:
            uploader.story(video, 'video', group_id=group_id)
        except Exception as e:
            logging.error("can't upload story\n")
            delete_split_tt_videos(tt_videos)
            return e

    delete_split_tt_videos(tt_videos)
