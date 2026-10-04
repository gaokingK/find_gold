from flask import Flask 

from app.routes.health import health_bp
from app.routes.bloggers import bloggers_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    app.register_blueprint(bloggers_bp)

    return app