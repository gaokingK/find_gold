# 此文件的目的是为了判断接口问题还是数据库问题
# 该脚本业务用途：排查故障时，如果接口报错，需要去欸等你给是应用层也就是API逻辑问题，还是底层数据存储连接问题

# 关注点分离
from app.db import get_connection

# 定义一个函数 建立连接然后关闭连接
def main():
    conn = get_connection()
# try...finally处理外部资源（文件、网络连接、数据库连接的最佳实践
    try:
        # cursor游标对象
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1 AS ok')
            row = cursor.fetchone()

# 将成功信息输出到标注输出流，用于人工确认或日志记录
        print('MySQL connection is OK:', row)

    finally:
        # 显式关闭数据库连接，防止连接泄露
        conn.close()

if __name__ == '__main__':
    main()
