import datetime as dt
import json
from typing import Optional
from http import HTTPStatus

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

import repository, models, schemas
from services import BotService, LoginService, TokenService
from database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

app = FastAPI()


origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.post('/v1/login', status_code=HTTPStatus.OK)
def login(login_info: schemas.LoginInfo,
          response: Response,
          db: Session = Depends(get_db)) -> dict:
    if LoginService.is_logged_in(
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

    return TokenService.create_token(username=login_info.username)


@app.post('/v1/user')
def create_user(login_info: schemas.LoginInfo, db: Session = Depends(get_db)):
    db_user = repository.create_user(
        db=db,
        username=login_info.username,
        password=login_info.password
    )

    # TODO if user already exists, raise HTTPException

    # TODO return userid
    return {'msg': 'User created!'}


@app.get('/v1/chatroom', status_code=HTTPStatus.OK)
def list_user_chatrooms(
    response: Response,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if not LoginService.is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    chatrooms = db.query(models.Chatroom).all()

    return chatrooms


@app.post('/v1/chatroom')
def create_chatroom(chatroom_info: schemas.ChatroomInfo, db: Session = Depends(get_db)) -> dict:
    db_chatroom = repository.create_chatroom(db=db, name=chatroom_info.name)

    return {'id': db_chatroom.uuid}


@app.post('/v1/chatroom/{chatroom_id}')
def post_message_to_chatroom(
    chatroom_id: str,
    response: Response,
    message_body: schemas.MessageBody,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if not LoginService.is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    if message_body.text.startswith('/stock='):
        BotService.post_stock(message_body=message_body, chatroom_id=chatroom_id)
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


@app.post('/v1/botchatroom/{id}')
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


@app.get('/v1/chatroom/{id}', status_code=HTTPStatus.OK)
def get_messages_from_chatroom(
    id: str,
    response: Response,
    x_user: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_sessionid: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if not LoginService.is_logged_in(username=x_user, token=x_token, session_id=x_sessionid):
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {'msg': 'please log in'}

    # TODO maybe save chatroom id at cache?
    chatroom_id = db.query(models.Chatroom).filter(models.Chatroom.uuid == id).first().id

    messages = (
        db.query(models.Message)
          .filter(models.Message.chatroom_id == chatroom_id)
          .order_by(models.Message.created_at.desc())
          .limit(50)
          .all()
    )

    messages.reverse()

    return messages
