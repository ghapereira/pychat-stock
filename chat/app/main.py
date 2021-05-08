from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
import redis


class LoginInfo(BaseModel):
    username: str
    password: str


app = FastAPI()

cache = redis.Redis(host='redis', port=6379)

@app.get('/')
def read_root() -> dict:
    with open('/var/data/db.txt', 'w+') as fp:
        fp.write('Data written!')
    return {'Hello': 'World'}


@app.post('/login')
def login(login_info: LoginInfo) -> dict:
    # verify login
    # if not logged in, log itself
    # if logged, refresh token
    count = get_hit_count()
    return f'Hello world! I have been seen {count} times.\n'

def get_hit_count() -> int:
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)


@app.get('/items/{item_id}')
def read_item(item_id: int, q: Optional[str] = None) -> dict:
    return {'item_id': item_id, 'q': q}
