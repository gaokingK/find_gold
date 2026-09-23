from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.get('/health')
def health():
    return jsonify(
        {
            'code': 0,
            'message': 'ok',
            'data': {
                'status': 'ok'
            }
        }
    )