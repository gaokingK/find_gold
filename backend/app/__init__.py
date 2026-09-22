from flask import Flask, jsonify

def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(
            {
                'code': 0,
                'message': "ok",
                "data": {
                    "status": "ok"
                }
            }
        )

    return app