import asyncio
from enum import Enum
from itertools import count

import aiohttp


class Status(Enum):
    New, Pending, Completed, Error = range(4)


class Task:
    _get_new_id = count()

    def __init__(self, url):
        self.id = next(self._get_new_id)
        self.url = url
        self.status = Status.New
        self.resp_content_length = 0
        self.resp_HTTP_status = 0
        self.resp_body = ""

    async def __call__(self):
        self.status = Status.Pending
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url) as resp:
                    if resp.status == 200:
                        self.status = Status.Completed
                    else:
                        self.status = Status.Error
                    self.resp_content_length = resp.headers \
                                                   .get('content-length', 0)
                    self.resp_body = await resp.text()
                    self.resp_HTTP_status = resp.status
            except Exception as e:
                print(f"EXCEPTION Task#{self.id}: {e}")
                self.status = Status.Error

    def __str__(self):
        return (f"ID = {self.id}\n"
                f"Url = {self.url}\n"
                f"Status = {self.status}\n"
                f"Response HTTP status = {self.resp_HTTP_status}\n"
                f"Response content length = {self.resp_content_length}")
