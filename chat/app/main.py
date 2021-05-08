from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
import redis
from sqlalchemy.orm import Session

import repository, models, schemas
from database import SessionLocal, engine


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
    with open('/var/data/db.txt', 'w+') as fp:
        fp.write('Data written!')
    return {'Hello': 'World'}


@app.post('/login')
def login(login_info: schemas.LoginInfo) -> dict:
    # verify login
    # if not logged in, log itself
    # if logged, refresh token
    count = get_hit_count()
    return f'Hello world! I have been seen {count} times.\n'


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
