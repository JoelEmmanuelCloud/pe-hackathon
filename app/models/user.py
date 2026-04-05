from datetime import datetime
from peewee import CharField, DateTimeField
from app.database import BaseModel


class User(BaseModel):
    username = CharField(unique=True, max_length=100)
    email = CharField(unique=True, max_length=255)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "users"
