from flask import jsonify

def success(data=None):
    return jsonify(
        {
            'code': 0,
            'message': 'ok',
            'data': data if data is not None else {}
        }
    )