from flask import request, Blueprint
# 导入request

from app.utils.responses import success, error
# 导入success是为了上一章中写好的jsonify（封装好的JSON格式）

# 注册蓝图，__name__实例（实例化蓝图对象，传入蓝图名称和当前模块名）
blogger_bp = Blueprint('bloggers', __name__)

# 使用装饰器注册路由，限定HTTP请求方法为GET，括号内是url 路径
@blogger_bp.get('/api/v1/bloggers')
def list_bloggers():
    # 通过request函数来获得参数（通过request代理对象获取URL查询参数）
    keyword = request.args.get('keyword', "")
    status = request.args.get('status', "")

    # 加入错误处理逻辑，如果keyword和status都为空，则返回错误响应(List)
    # List是有序的元素集合，只能通过索引或者直接遍历/包含判断来访问
    allowed_status = ["active", "observing"]

# 如果status有值，并且这个值不在允许的列表里，那么就执行下面的报错逻辑
    if status and status not in allowed_status:
        # 调用了一个错误处理函数，该函数通常会将参数封装成JSON格式返回给前端
        return error(
            code='VALIDATION_ERROR',
            message='status参数不合法',
            details=[
                {
                    'field': 'status',
                    'message': f'status参数必须是{allowed_status}里面的其中一个值'
                }
            ],
            http_status=400
        )

# 返回上一章中写好的success里面的jsonify格式的函数（调用封装的success工具函数，返回JSON格式的HTTP响应）
    return success(
        {
            'keyword': keyword,
            'status': status
        }
    )