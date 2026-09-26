from flask import request, Blueprint
# 导入request

from app.utils.responses import success
# 导入success是为了上一章中写好的jsonify（封装好的JSON格式）

# 注册蓝图，__name__实例（实例化蓝图对象，传入蓝图名称和当前模块名）
blogger_bp = Blueprint('bloggers', __name__)

# 使用装饰器注册路由，限定HTTP请求方法为GET，括号内是url 路径
@blogger_bp.get('/api/v1/bloggers')
def list_bloggers():
    # 通过request函数来获得参数（通过request代理对象获取URL查询参数）
    keyword = request.args.get('keyword', "")
    status = request.args.get('status', "")

# 返回上一章中写好的success里面的jsonify格式的函数（调用封装的success工具函数，返回JSON格式的HTTP响应）
    return success(
        {
            'keyword': keyword,
            'status': status
        }
    )