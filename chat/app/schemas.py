from typing import List, Optional

from pydantic import BaseModel


class BaseRequest(BaseModel):
    token: Optional[str]
    session_id: Optional[str]


class LoginInfo(BaseRequest):
    username: str
    password: Optional[str]
