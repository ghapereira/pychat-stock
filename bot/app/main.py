from typing import Optional

from fastapi import FastAPI
import requests

app = FastAPI()


@app.get('/')
def read_root() -> dict:
    r = requests.get('http://chat')
    return {'From bot': r.text}


@app.get('/items/{item_id}')
def read_item(item_id: int, q: Optional[str] = None) -> dict:
    return {'item_id': item_id, 'q': q}
