import datetime as dt
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
from pydantic import BaseModel
import redis
from sqlalchemy.orm import Session

import repository, models, schemas
from database import SessionLocal, engine


CACHE_EXPIRE_TIME_SECONDS = 300
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
NUM_REDIS_RETRIES = 5


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


@app.get('/')
def read_root() -> dict:
    return {'Hello': 'World'}


@app.post('/login', status_code=HTTPStatus.OK)
def login(login_info: schemas.LoginInfo,
          response: Response,
          db: Session = Depends(get_db)) -> dict:
    # TODO: move logic to repository/services

    if is_logged_in(login_info):
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


def is_logged_in(login_info: schemas.LoginInfo) -> bool:
    print('\tIn is_logged_in')
    if login_info.token is None or login_info.session_id is None:
        return False

    print('\tThere are token and session_id')

    session_token = get_session_token_from_cache(
        username=login_info.username,
        session_id=login_info.session_id,
        token=login_info.token
    )

    print(f'\tSession token is {session_token}')

    valid_token = (session_token is not None) and (str(session_token, 'utf-8') == login_info.token)
    print(f'valid_token was deemed {valid_token}')

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

    return {'msg': 'User created!'}


@app.get('/items/{item_id}')
def read_item(item_id: int, q: Optional[str] = None) -> dict:
    return {'item_id': item_id, 'q': q}
