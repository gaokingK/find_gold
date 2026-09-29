# 此文件的目的是为了判断接口问题还是数据库问题

from app.db import get_connection

# 定义一个函数 建立连接然后关闭连接
def main():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1 AS ok')
            row = cursor.fetchone()

        print('MySQL connection is OK:', row)

    finally:
        conn.close()

if __name__ == '__main__':
    main()
