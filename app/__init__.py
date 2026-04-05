import logging
import os
from flask import Flask
from pythonjsonlogger import jsonlogger
from dotenv import load_dotenv

load_dotenv()


def create_app(db=None):
    app = Flask(__name__)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    from app.database import database_proxy, get_db
    if db is None:
        db = get_db()
    database_proxy.initialize(db)

    @app.before_request
    def connect_db():
        if db.is_closed():
            db.connect()

    @app.teardown_appcontext
    def close_db(exc):
        if not db.is_closed():
            db.close()

    from app.routes import register_routes
    register_routes(app)

    app.logger.info("App started", extra={"env": os.getenv("FLASK_ENV", "production")})
    return app
