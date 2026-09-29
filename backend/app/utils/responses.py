from flask import jsonify

# 定义一个关于成功响应的函数，返回包含一个关于code,message,data的JSON对象
def success(data=None):
    return jsonify(
        {
            'code': 0,
            'message': 'ok',
            'data': data if data is not None else {}
        }
    )

# 定义一个关于错误响应的函数，返回包含一个关于code,message,details的JSON对象
def error(code, message, details=None, http_status=400):
    if details is None:
        details = []

    return jsonify(
        {
            'code': code,
            'message': message,
            'details': details
        }
    ), http_status