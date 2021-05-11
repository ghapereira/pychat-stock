import datetime as dt
import json
import time
from typing import Optional
import uuid

import pika
import redis

import schemas


SENDING_QUEUE = 'requeststock'
STOCK_BOT_NAME = 'stockbot'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
CACHE_EXPIRE_TIME_SECONDS = 300
NUM_REDIS_RETRIES = 5


class LoginService:

    @staticmethod
    def is_logged_in(username: Optional[str], token: Optional[str], session_id: Optional[str]) -> bool:
        if None in [username, token, session_id]:
            return False

        session_token = CacheService.get_session_token_from_cache(
            username=username,
            session_id=session_id
        )

        valid_token = (session_token is not None) and (str(session_token, 'utf-8') == token)

        return valid_token


class TokenService:
    TOKEN_EXPIRATION_FACTOR = 0.8
    TOKEN_INFORMED_EXPIRATION_SECONDS = CACHE_EXPIRE_TIME_SECONDS * TOKEN_EXPIRATION_FACTOR

    @staticmethod
    def create_token(username: str) -> dict:
        token = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        CacheService.save_token_to_cache(username=username, session_id=session_id, token=token)
        expire_time = dt.datetime.now() + dt.timedelta(seconds=TokenService.TOKEN_EXPIRATION_FACTOR)

        return {'token': token, 'session_id': session_id, 'expires_in': expire_time.strftime(DATE_FORMAT)}

    @staticmethod
    def refresh_token(username: str, session_id: str) -> dict:
        token = str(uuid.uuid4())
        CacheService.save_token_to_cache(username=username, session_id=session_id, token=token)
        expire_time = dt.datetime.now() + dt.timedelta(seconds=TokenService.TOKEN_EXPIRATION_FACTOR)

        return {'token': token, 'session_id': session_id, 'expires_in': expire_time.strftime(DATE_FORMAT)}


class CacheService:

    cache = None

    @staticmethod
    def save_token_to_cache(username: str, session_id: str, token: str) -> None:
        if CacheService.cache is None:
            CacheService.cache = redis.Redis(host='redis', port=6379)

        retries = NUM_REDIS_RETRIES
        while True:
            try:
                CacheService.cache.setex(
                    name=f'{username}:{session_id}',
                    time=CACHE_EXPIRE_TIME_SECONDS,
                    value=token
                )
                return
            except redis.exceptions.ConnectionError as exc:
                if retries == 0:
                    raise exc
                retries -= 1
                time.sleep(0.5)


    @staticmethod
    def get_session_token_from_cache(username: str, session_id: str) -> Optional[str]:
        if CacheService.cache is None:
            CacheService.cache = redis.Redis(host='redis', port=6379)

        retries = NUM_REDIS_RETRIES
        while True:
            try:
                return CacheService.cache.get(name=f'{username}:{session_id}')
            except redis.exceptions.ConnectionError as exc:
                if retries == 0:
                    raise exc
                retries -= 1
                time.sleep(0.5)


class BotService:
    def __init__(self, message_body: schemas.MessageBody, chatroom_id: str) -> None:
        self._stockname = message_body.text.split('=')[1]
        self._chatroom_id = chatroom_id

    def post_stock(self) -> bool:
        try:
            self._send_message_to_queue()
        except pika.exceptions.AMQPConnectionError:
            return False

        return True

    def _send_message_to_queue(self) -> None:
        credentials = pika.PlainCredentials('admin', 'admin')
        connection_parameters = pika.ConnectionParameters(
            host='rabbitmq',
            credentials=credentials
        )

        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()

        channel.queue_declare(queue=SENDING_QUEUE)

        outgoing = {
            'stock_code': self._stockname,
            'chatroom': self._chatroom_id,
            'bot_name': STOCK_BOT_NAME
        }

        channel.basic_publish(
            exchange='',
            routing_key=SENDING_QUEUE,
            body=json.dumps(outgoing)
        )
        connection.close()
