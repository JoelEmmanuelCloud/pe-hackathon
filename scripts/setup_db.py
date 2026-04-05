from dotenv import load_dotenv
load_dotenv()

from app.database import database_proxy, get_db
from app.models.user import User
from app.models.url import Url
from app.models.event import Event

db = get_db()
database_proxy.initialize(db)

with db:
    db.create_tables([User, Url, Event], safe=True)
    print("Tables created: users, urls, events")
