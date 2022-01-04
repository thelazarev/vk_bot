from __future__ import annotations

import json
import time
import logging
from random import random
from abc import ABC, abstractmethod
from datetime import datetime
import functools

from vk_api.utils import get_random_id

from utils.tiktok_utils import post_tt_video

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)8s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

users = dict()

def spam_check(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        sender = args[2]
        if sender in users:
            if (datetime.now() - users[sender]).seconds < 20:
                return False
        is_executed = func(*args, **kwargs)
        if is_executed:
            users[sender] = datetime.now()

        return is_executed
    return wrapper_decorator


class VkCommand(ABC):

    @abstractmethod
    def execute(self, event, sender) -> None:
        pass


class SimpleAnswerCommand(VkCommand):

    def __init__(self, vk, uploader) -> None:
        self._vk = vk
        self._uploader = uploader
        with open('answers.json', 'r') as answers:
            self._answers = json.load(answers)

    @spam_check
    def execute(self, event, sender) -> bool:

        if random() > 0.05:
            return False

        peer_id = event.obj.get('peer_id')
        message: str = event.obj.get('text')

        self._vk.messages.setActivity(peer_id=peer_id, type="typing")
        time.sleep(5)
        response_message = self._answers[message]

        try:
            self._vk.messages.send(peer_id=peer_id,
                                   message=response_message,
                                   random_id=get_random_id())
        except Exception as e:
            logging.error(f"can't send vk message\n {e}")
            return False

        return True


class PostTiktokStoryCommand(VkCommand):

    def __init__(self, vk, uploader, group_id) -> None:
        self._vk = vk
        self._uploader = uploader
        self._group_id = group_id

    @spam_check
    def execute(self, event, sender) -> bool:
        post_tt_video(self._vk, self._uploader, self._group_id, event)
        return True


class Invoker():

    def __init__(self, vk, uploader, group_id) -> None:
        self.commands = dict()
        self.simple_answer_command = SimpleAnswerCommand(vk, uploader)
        self.post_tiktok_story_command = PostTiktokStoryCommand(vk, uploader, group_id)

    def execute_vk_command(self, command, event):
        command.execute(event)

    def parse_vk_event(self, event):
        tiktok_urls = ['https://vm.tiktok.com', 'https://www.tiktok.com', 'https://m.tiktok.com']

        message: str = event.obj.get('text')
        sender = event.obj.get('from_id')

        for tiktok_url in tiktok_urls:
            if message.find(tiktok_url) != -1:
                self.post_tiktok_story_command.execute(event, sender)

        if message.lower() in self.simple_answer_command._answers:
            self.simple_answer_command.execute(event, sender)
