from datetime import datetime
from peewee import CharField, DateTimeField, ForeignKeyField, TextField
from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    url = ForeignKeyField(Url, backref="events")
    user = ForeignKeyField(User, backref="events", null=True)
    event_type = CharField(max_length=50)
    timestamp = DateTimeField(default=datetime.now)
    details = TextField(null=True)

    class Meta:
        table_name = "events"
