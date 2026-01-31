from asyncio import Queue

from app_server.config.di import DI
from zmq.asyncio import asyncio

injector: DI
# 応答待ち用: request_id -> asyncio.Queue（main.py の受信タスクと order 層で共有）
pending_response_queues: dict[str, Queue | None] | None = None
pending_response_lock: asyncio.Lock | None = None
