import datetime as dt
import hashlib
import os
import uuid

from sqlalchemy.orm import Session

import models, schemas


HASH_SALT_LEN = 32
HASH_ITERATIONS = 100000
HASH_ALGORITHM = 'sha256'
PASSWORD_ENCODING = 'utf-8'


# TODO move to services
def check_password(db: Session, username: str, user_password: str) -> bool:
    asked_user = db.query(models.User).filter(models.User.username == username).first()

    salt = asked_user.hashed_password[:HASH_SALT_LEN]
    key = asked_user.hashed_password[HASH_SALT_LEN:]

    new_key = hashlib.pbkdf2_hmac(
        hash_name=HASH_ALGORITHM,
        password=user_password.encode(PASSWORD_ENCODING),
        salt=salt,
        iterations=HASH_ITERATIONS
    )

    return key == new_key


# Following https://nitratine.net/blog/post/how-to-hash-passwords-in-python/
def create_user(db: Session, username: str, password: str) -> models.User:
    salt = os.urandom(HASH_SALT_LEN)
    key = hashlib.pbkdf2_hmac(
        hash_name=HASH_ALGORITHM,
        password=password.encode(PASSWORD_ENCODING),
        salt=salt,
        iterations=HASH_ITERATIONS
    )

    hashed_password = salt + key

    db_user = models.User(
        username=username,
        hashed_password=hashed_password,
        created_at=dt.datetime.now()
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def create_chatroom(db: Session, name: str) -> models.Chatroom:
    chatroom_uuid = str(uuid.uuid4())

    db_chatroom = models.Chatroom(
        uuid=chatroom_uuid,
        name=name,
        created_at=dt.datetime.now()
    )

    db.add(db_chatroom)
    db.commit()
    db.refresh(db_chatroom)

    return db_chatroom


def create_message(db: Session, text: str, owner_id: int, chatroom_id: int) -> models.Message:
    message_uuid = str(uuid.uuid4())

    db_message = models.Message(
        uuid=message_uuid,
        text=text,
        owner_id=owner_id,
        chatroom_id=chatroom_id,
        created_at=dt.datetime.now()
    )

    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    return db_message
