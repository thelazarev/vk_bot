import logging
import re
from pathlib import Path

import urllib3


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
    return download_address.search(str(tt_page_content.data)).group(1)


def download_tt_video(url, name):
    tt_page_content = download_data(url)
    tt_video_link = video_url_parse(tt_page_content)
    tt_video = download_data(tt_video_link)

    tmp_directory = f'{Path(__file__).resolve().parent.parent}/tmp'

    with open(f'{tmp_directory}/{name}', "wb") as f:
        f.write(tt_video.data)

    return f'{tmp_directory}/{name}'
