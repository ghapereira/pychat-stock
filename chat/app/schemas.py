from typing import List, Optional

from pydantic import BaseModel


class BaseRequest(BaseModel):
    token: Optional[str]
    session_id: Optional[str]
    username: str

class LoginInfo(BaseRequest):
    password: Optional[str]


class ChatroomInfo(BaseModel):
    name: str


class MessageBody(BaseModel):
    text: str


class BotMessageBody(MessageBody):
    bot_name: str
