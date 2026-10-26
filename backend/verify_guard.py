import os, sys

os.environ['DB_NAME'] = 'fund_db'

sys.path.insert(0, 'tests')

import conftest

print("开始执行守卫断言")
conftest.assert_test_database()
print("守卫断言执行完毕")