# 此文件的目的是为了避免重复代码*（代码复用/DRY原则）
# 配置分离（配置与代码分离的最佳司吉安，便于再不同环境开发。测试、生产之间切换配置
from pymysql import connect

from app.config import DB_CONFIG

def get_connection():
    # 解包/关键字参数展开关键字传参
    return connect(**DB_CONFIG)