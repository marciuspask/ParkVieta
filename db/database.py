import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_engine() -> Engine:
    url = os.environ["DATABASE_URL"]
    return create_engine(url)
