from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    TIMESTAMP
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    uuid = Column(String, index=True, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    last_login = Column(TIMESTAMP)

    messages = relationship('Message', back_populates='owner')
    user_chatrooms = relationship('UserChatroom', back_populates='user')
    logins = relationship('Login', back_populates='user')


class Chatroom(Base):
    __tablename__ = 'chatrooms'

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True, unique=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)

    messages = relationship('Message', back_populates='chatroom')
    chatroom_users = relationship('UserChatroom', back_populates='chatroom')


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True, unique=True)
    owner_id = Column(Integer, ForeignKey('users.id'))
    chatroom_id = Column(Integer, ForeignKey('chatrooms.id'))

    is_valid = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP)
    text = Column(String)

    owner = relationship('User', back_populates='messages')
    chatroom = relationship('Chatroom', back_populates='messages')


class UserChatroom(Base):
    __tablename__ = 'users_chatrooms'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    chatroom_id = Column(Integer, ForeignKey('chatrooms.id'))

    user = relationship('User', back_populates='user_chatrooms')
    chatroom = relationship('Chatroom', back_populates='chatroom_users')


class Login(Base):
    __tablename__ = 'login'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP)
    ended_at = Column(TIMESTAMP)

    user = relationship('User', back_populates='logins')
