import datetime as dt
import json
from typing import Optional
from http import HTTPStatus
import uuid

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response
)
import pika
from pydantic import BaseModel
import redis
from sqlalchemy.orm import Session

import repository, models, schemas
from database import SessionLocal, engine


CACHE_EXPIRE_TIME_SECONDS = 300
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
NUM_REDIS_RETRIES = 5
SENDING_QUEUE = 'requeststock'
STOCK_BOT_NAME = 'stockbot'


models.Base.metadata.create_all(bind=engine)
cache = redis.Redis(host='redis', port=6379)
app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get('/', status_code=HTTPStatus.OK)
def read_root(
    response: Response,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None)
) -> dict:
    if not is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    return {'Hello': 'World'}


@app.post('/login', status_code=HTTPStatus.OK)
def login(login_info: schemas.LoginInfo,
          response: Response,
          db: Session = Depends(get_db)) -> dict:
    # TODO: move logic to repository/services

    if is_logged_in(
        username=login_info.username,
        token=login_info.token,
        session_id=login_info.session_id
    ):
        return refresh_token(username=login_info.username, session_id=login_info.session_id)

    # TODO: catch error on unexistent user
    if login_info.password is None:
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'login failed, password must not be empty'}

    password_ok = repository.check_password(
        db=db,
        username=login_info.username,
        user_password=login_info.password
    )

    if not password_ok:
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'login failed'}

    return create_token(username=login_info.username)


def create_token(username: str):
    token = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    save_token_to_cache(username=username, session_id=session_id, token=token)
    expire_time = dt.datetime.now() + dt.timedelta(seconds=CACHE_EXPIRE_TIME_SECONDS * 0.8)

    return {'token': token, 'session_id': session_id, 'expires_in': expire_time.strftime(DATE_FORMAT)}


def refresh_token(username: str, session_id: str) -> dict:
    token = str(uuid.uuid4())
    save_token_to_cache(username=username, session_id=session_id, token=token)
    expire_time = dt.datetime.now() + dt.timedelta(seconds=CACHE_EXPIRE_TIME_SECONDS * 0.8)

    return {'token': token, 'session_id': session_id, 'expires_in': expire_time.strftime(DATE_FORMAT)}


def is_logged_in(username: Optional[str], token: Optional[str], session_id: Optional[str]) -> bool:
    # TODO maybe use any?
    if username is None or token is None or session_id is None:
        return False

    session_token = get_session_token_from_cache(
        username=username,
        session_id=session_id,
        token=token
    )

    valid_token = (session_token is not None) and (str(session_token, 'utf-8') == token)

    return valid_token


def save_token_to_cache(username: str, session_id: str, token: str) -> None:
    retries = NUM_REDIS_RETRIES
    while True:
        try:
            cache.setex(
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


def get_session_token_from_cache(username: str, session_id: str, token: str) -> Optional[str]:
    retries = NUM_REDIS_RETRIES
    while True:
        try:
            return cache.get(name=f'{username}:{session_id}')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.post('/user')
def create_user(login_info: schemas.LoginInfo, db: Session = Depends(get_db)):
    # retrieve user from db
    # if user already exists, raise HTTPException

    db_user = repository.create_user(
        db=db,
        username=login_info.username,
        password=login_info.password
    )

    # return userid
    return {'msg': 'User created!'}


@app.get('/chatroom', status_code=HTTPStatus.OK)
def list_user_chatrooms(
    response: Response,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None)
) -> dict:
    if not is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    # TODO: return a query of all chatrooms the user has access to
    return {}


@app.post('/chatroom')
def create_chatroom(chatroom_info: schemas.ChatroomInfo, db: Session = Depends(get_db)) -> dict:
    db_chatroom = repository.create_chatroom(db=db, name=chatroom_info.name)

    return {'id': db_chatroom.uuid}


@app.post('/chatroom/{chatroom_id}')
def post_message_to_chatroom(
    chatroom_id: str,
    response: Response,
    message_body: schemas.MessageBody,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if not is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    # parse message if it is to a bot
    if message_body.text.startswith('/stock='):
        stockname = message_body.text.split('=')[1]

        credentials = pika.PlainCredentials('admin', 'admin')
        connection_parameters = pika.ConnectionParameters(
            host='rabbitmq',
            credentials=credentials
        )

        connection = pika.BlockingConnection(connection_parameters)
        channel = connection.channel()

        channel.queue_declare(queue=SENDING_QUEUE)

        outgoing = {
            'stock_code': stockname,
            'chatroom': chatroom_id,
            'bot_name': STOCK_BOT_NAME
        }

        channel.basic_publish(
            exchange='',
            routing_key=SENDING_QUEUE,
            body=json.dumps(outgoing)
        )
        connection.close()

        return {'msg': 'stock request posted'}

    owner_id = db.query(models.User).filter(models.User.username == x_user).first().id
    chatroom_id = db.query(models.Chatroom).filter(models.Chatroom.uuid == chatroom_id).first().id

    db_message = repository.create_message(
        db=db,
        text=message_body.text,
        owner_id=owner_id,
        chatroom_id=chatroom_id
    )

    return {'msg': 'message posted'}


@app.post('/botchatroom/{id}')
def post_bot_message_to_chatroom(
    id: str,
    message_body: schemas.BotMessageBody,
    db: Session = Depends(get_db)
) -> dict:
    bot_list = db.query(models.User).filter(models.User.username == message_body.bot_name).all()
    if not bot_list:
        bot_user = repository.create_user(
            db=db,
            username=message_body.bot_name,
            password=message_body.bot_name
        )
        bot_list = [bot_user]

    owner_id = bot_list[0].id
    chatroom_id = db.query(models.Chatroom).filter(models.Chatroom.uuid == id).first().id

    db_message = repository.create_message(
        db=db,
        text=message_body.text,
        owner_id=owner_id,
        chatroom_id=chatroom_id
    )

    return {'msg': 'message posted'}


@app.get('/chatroom/{id}', status_code=HTTPStatus.OK)
def get_messages_from_chatroom(
    id: str,
    response: Response,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if not is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    # TODO maybe save chatroom id at cache?
    chatroom_id = db.query(models.Chatroom).filter(models.Chatroom.uuid == id).first().id

    messages = (
        db.query(models.Message)
          .filter(models.Message.chatroom_id == chatroom_id)
          .order_by(models.Message.created_at.asc())
          .limit(50)
          .all()
    )

    return messages
