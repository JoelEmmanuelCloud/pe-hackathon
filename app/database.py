import os
from peewee import PostgresqlDatabase, Model, DatabaseProxy

database_proxy = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy


def get_db():
    return PostgresqlDatabase(
        os.getenv("DB_NAME", "hackathon_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
    )
