from datetime import datetime
from peewee import CharField, TextField, BooleanField, DateTimeField, ForeignKeyField
from app.database import BaseModel
from app.models.user import User


class Url(BaseModel):
    user = ForeignKeyField(User, backref="urls", null=True)
    short_code = CharField(unique=True, max_length=20)
    original_url = TextField()
    title = CharField(null=True, max_length=255)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)


    class Meta:
        table_name = "urls"
