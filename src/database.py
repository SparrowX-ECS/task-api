import os
from urllib.parse import quote_plus

from sqlmodel import create_engine


def database_url_from_environment() -> str:
    host = os.environ["DB_HOST"]
    port = os.getenv("DB_PORT", "5432")
    database = os.environ["DB_NAME"]
    username = quote_plus(os.environ["DB_USERNAME"])
    password = quote_plus(os.environ["DB_PASSWORD"])
    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"


def create_database_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)
