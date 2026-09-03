from flask import Flask

from .config import Config
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.template_filter("money")
    def money_filter(price_cents):
        return f"${price_cents / 100:,.2f}"

    register_routes(app)

    return app
