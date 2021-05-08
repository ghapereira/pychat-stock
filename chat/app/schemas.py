from typing import List, Optional

from pydantic import BaseModel


class LoginInfo(BaseModel):
    username: str
    password: str
