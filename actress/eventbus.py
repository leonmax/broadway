import asyncio
import functools
import os
import random
from collections import namedtuple
from signal import SIGINT, SIGTERM
import signal
import time

__author__ = 'leonmax'

Message = namedtuple('Message', ['channel', 'data'])


class DummyLoader():
    def load(self, raw_data):
        return raw_data

class EventBus():
    def subscribe(self, channel, handlers, loader=None):
        raise NotImplementedError()

    def unsubscribe(self, channel, handlers):
        raise NotImplementedError()

    @asyncio.coroutine
    def publish(self, channel, data):
        raise NotImplementedError()

class BasicEventBus(EventBus):
    def __init__(self, loop=None):
        self.loop = loop if loop else asyncio.get_event_loop()
        self._loaders = {}
        self._bus = asyncio.Queue()
        self._subscribers = {}

    def backlog(self):
        return self._bus.qsize()

    def subscribe(self, channel, handlers, loader=None):
        if loader:
            self._loaders[channel] = loader
        channel_handlers = self._subscribers.setdefault(channel, [])
        channel_handlers += handlers

    def unsubscribe(self, channel, handlers):
        if channel in self._subscribers:
            self._subscribers[channel] -= handlers

    @asyncio.coroutine
    def publish(self, channel, data):
        msg = Message(channel, data)
        yield from self._bus.put(msg)

    @asyncio.coroutine
    def start(self):
        while True:
            msg = yield from self._bus.get()
            event = self._loaders.setdefault(msg.channel, DummyLoader()).load(msg.data)
            if msg.channel in self._subscribers:
                for handler in self._subscribers[msg.channel]:
                    self.loop.create_task(handler(event))

    def run_forever(self):
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

if __name__ == "__main__":

    class Runner():
        def __init__(self, name):
            self.name = name
            self.count = 0
            self.last = None

        @asyncio.coroutine
        def process(self, event):
            self.count += 1
            print(self.name, event, self.count)
            # if self.count % 10000 == 0:
            #     now = time.time()
            #     if self.last:
            #         print("ratio: %s" % (10000/(now - self.last)))
            #     self.last = now

    @asyncio.coroutine
    def hello_world():
        while True:
            seed = random.random()
            if seed < 0.5:
                channel = "/hello"
            else:
                channel = "/bye"
            yield from bus.publish(channel, "world")
            yield from asyncio.sleep(0.1)

    bus = BasicEventBus()
    bus.subscribe("/hello", [Runner("hello").process])
    bus.subscribe("/bye", [Runner("bye").process])

    asyncio.Task(bus.start())
    asyncio.Task(hello_world())
    bus.run_forever()