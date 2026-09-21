# 技术规格文档 v1.0

---

## 1. 系统架构

### 1.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue.js/React)                    │
│  - 博主管理界面                                                │
│  - 截图上传界面                                                │
│  - 数据展示界面                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     后端 API (Flask)                          │
│  /api/bloggers       - 博主 CRUD                              │
│  /api/funds          - 基金 CRUD                              │
│  /api/screenshots    - 截图上传与处理                          │
│  /api/operations     - 操作记录管理                            │
│  /api/nav            - 净值数据获取                            │
│  /api/returns        - 收益计算                               │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │  MySQL   │   │ Umi-OCR  │   │ 外部API  │
        │ 数据库    │   │  服务     │   │ (净值)   │
        └──────────┘   └──────────┘   └──────────┘
```

### 1.2 技术栈

| 层级 | 技术选型 | 版本 |
|------|---------|------|
| 前端框架 | Vue.js 3 或 React 18 | - |
| 前端UI | Element Plus / Ant Design | - |
| 后端框架 | Python Flask | 2.x |
| ORM | SQLAlchemy | 2.x |
| 数据库 | MySQL | 8.0 |
| OCR服务 | Umi-OCR | 最新版 |
| Web服务器 | Gunicorn + Nginx | - |
| 进程管理 | Supervisor | - |

---

## 2. 数据库设计

### 2.1 ER图

```
┌─────────────┐       ┌─────────────┐
│  bloggers   │       │   funds     │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ name        │
│ sector      │       │ fund_code   │
│ observe_    │       └──────┬──────┘
│ start_date  │              │
└──────┬──────┘              │
       │                     │
       │  ┌──────────────────┴──────────────────┐
       │  │                                     │
       ▼  ▼                                     ▼
┌─────────────────┐                    ┌─────────────────┐
│initial_positions│                    │   operations    │
├─────────────────┤                    ├─────────────────┤
│ id (PK)         │                    │ id (PK)         │
│ blogger_id (FK) │◄───────────────────│ blogger_id (FK) │
│ fund_id (FK)    │                    │ fund_id (FK)    │
│ shares          │                    │ operation_date  │
│ cost_amount     │                    │ operation_type  │
│ record_date     │                    │ amount          │
└─────────────────┘                    │ shares          │
                                       │ screenshot_id   │
                                       └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │  screenshots    │
                                       ├─────────────────┤
                                       │ id (PK)         │
                                       │ file_path       │
                                       │ operation_date  │
                                       │ ocr_raw_text    │
                                       │ ocr_parsed_data │
                                       └─────────────────┘

                                       ┌─────────────────┐
                                       │  nav_history    │
                                       ├─────────────────┤
                                       │ id (PK)         │
                                       │ fund_id (FK)    │
                                       │ nav_date        │
                                       │ nav             │
                                       └─────────────────┘
```

### 2.2 SQL 建表语句

详见 `database/schema.sql` (待创建)

---

## 3. API 接口设计

### 3.1 博主管理 API

#### 获取博主列表
```
GET /api/bloggers

Query参数:
- sector: 按板块过滤(可选)
- status: 按状态过滤(active/observing/inactive)
- sort_by: 排序字段(name/observe_days/return_rate)
- order: 排序方式(asc/desc)

响应:
{
  "code": 0,
  "data": {
    "bloggers": [
      {
        "id": 1,
        "name": "张三",
        "sector": "消费板块",
        "observe_start_date": "2024-01-01",
        "observe_days": 200,
        "status": "active",
        "return_rate": 0.156,
        "total_profit": 12345.67
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### 添加博主
```
POST /api/bloggers

请求体:
{
  "name": "张三",
  "sector": "消费板块",
  "observe_start_date": "2024-01-01"
}

响应:
{
  "code": 0,
  "data": {
    "id": 1,
    "name": "张三",
    "sector": "消费板块",
    "observe_start_date": "2024-01-01"
  }
}
```

### 3.2 截图上传 API

#### 上传截图
```
POST /api/screenshots/upload

请求体 (multipart/form-data):
- operation_date: "2024-07-20" (必需)
- files: [File1, File2, ...] (支持批量上传)

响应:
{
  "code": 0,
  "data": {
    "screenshots": [
      {
        "id": 1,
        "file_path": "/uploads/2024/07/20/xxx.png",
        "ocr_result": {
          "raw_text": "博主: 张三\n基金名称: ...",
          "parsed_records": [
            {
              "blogger_name": "张三",
              "fund_name": "易方达消费行业",
              "operation": 1000.0,
              "duplicates": []
            }
          ]
        },
        "status": "pending"
      }
    ]
  }
}
```

#### 确认操作记录
```
POST /api/screenshots/{screenshot_id}/confirm

请求体:
{
  "records": [
    {
      "blogger_id": 1,
      "fund_name": "易方达消费行业",
      "operation": 1000.0,
      "is_new_fund": false,
      "action": "accept"  // accept/reject/edit
    }
  ]
}

响应:
{
  "code": 0,
  "message": "Records confirmed successfully"
}
```

### 3.3 收益计算 API

#### 获取博主收益详情
```
GET /api/returns/{blogger_id}

Query参数:
- as_of_date: 计算截止日期(默认今天)

响应:
{
  "code": 0,
  "data": {
    "blogger": {
      "id": 1,
      "name": "张三",
      "sector": "消费板块"
    },
    "status": "active",
    "observe_days": 200,
    "returns": {
      "total_cost": 100000.0,
      "total_market_value": 115678.90,
      "profit": 15678.90,
      "return_rate": 0.1568,
      "max_drawdown": -0.0823
    },
    "positions": [
      {
        "fund_name": "易方达消费行业",
        "shares": 15000.5,
        "cost_basis": 50000.0,
        "current_nav": 3.456,
        "market_value": 51841.73,
        "profit": 1841.73
      }
    ],
    "operation_frequency": {
      "total_operations": 45,
      "monthly": {"2024-01": 5, "2024-02": 8, ...}
    }
  }
}
```

### 3.4 净值数据 API

#### 获取基金净值
```
GET /api/nav/{fund_id}

Query参数:
- from_date: 开始日期
- to_date: 结束日期

响应:
{
  "code": 0,
  "data": {
    "fund_id": 1,
    "fund_name": "易方达消费行业",
    "nav_history": [
      {"date": "2024-07-19", "nav": 3.456},
      {"date": "2024-07-18", "nav": 3.450}
    ]
  }
}
```

#### 同步净值数据
```
POST /api/nav/sync

请求体:
{
  "fund_ids": [1, 2, 3],  // 可选,不传则同步所有
  "from_date": "2024-01-01"
}

响应:
{
  "code": 0,
  "data": {
    "synced_funds": 100,
    "synced_records": 5000,
    "errors": []
  }
}
```

---

## 4. Umi-OCR 集成

### 4.1 部署方式

Umi-OCR 以 HTTP 服务方式运行,通过 API 调用:

```bash
# 启动 Umi-OCR HTTP 服务
Umi-OCR.exe --host 127.0.0.1 --port 1224
```

### 4.2 API 调用示例

```python
import requests
import base64

def call_umi_ocr(image_path):
    """调用 Umi-OCR API"""
    url = "http://127.0.0.1:1224/api/ocr"
    
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    payload = {
        "base64": image_base64,
        "language": "chs",
        "is_dense": True
    }
    
    response = requests.post(url, json=payload, timeout=10)
    result = response.json()
    
    if result.get('code') == 100:
        return result.get('data', '')
    else:
        raise Exception(f"OCR failed: {result}")
```

### 4.3 资源占用

- **内存**: 约 500MB-1GB (取决于模型)
- **CPU**: 识别时占用较高,空闲时较低
- **建议**: 1C1G 服务器可能需要优化或升级

---

## 5. 净值数据获取

### 5.1 天天基金 API

天天基金(1234567.com)提供基金净值查询接口:

```python
import requests

def get_fund_nav(fund_code):
    """获取基金净值(天天基金 API)"""
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    
    response = requests.get(url, timeout=10)
    # 返回格式: jsonpgz({"fundcode":"000001","name":"华夏成长",...})
    
    # 解析 JSONP
    text = response.text
    json_str = text[text.index('(')+1 : text.rindex(')')]
    data = json.loads(json_str)
    
    return {
        "fund_code": data['fundcode'],
        "fund_name": data['name'],
        "nav": float(data['gsz']),  # 估值净值
        "nav_date": data['gztime']
    }
```

### 5.2 历史净值获取

```python
def get_fund_nav_history(fund_code, from_date, to_date):
    """获取历史净值"""
    url = f"http://api.fund.eastmoney.com/f10/lsjz"
    
    params = {
        "fundCode": fund_code,
        "pageIndex": 1,
        "pageSize": 100,
        "startDate": from_date,
        "endDate": to_date
    }
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    return data['Data']['LSJZList']
```

### 5.3 注意事项

- **频率限制**: 建议每次请求间隔 1-2 秒
- **缓存策略**: 每日净值更新后缓存,避免重复请求
- **错误处理**: 准备备用数据源

---

## 6. 前端设计

### 6.1 页面结构

```
/ (首页)
  - 博主总览(按板块分组,显示收益率排名)

/blogger/:id (博主详情页)
  - 基本信息
  - 收益指标
  - 持仓列表
  - 操作历史
  - 持仓分布图
  - 操作频率图

/upload (上传页)
  - 日期选择
  - 截图上传(支持拖拽)
  - OCR 结果预览
  - 去重提示
  - 确认提交

/history (历史记录页)
  - 截图归档
  - OCR 结果查看
  - 操作记录查询

/settings (设置页)
  - 博主管理
  - 初始持仓录入
  - 净值同步
```

### 6.2 前端技术栈

- **Vue 3** + **Element Plus**
- **ECharts** 用于图表(持仓分布、操作频率)
- **Axios** 用于 API 请求

---

## 7. 后端设计

### 7.1 项目结构

```
fund2/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── blogger.py
│   │   ├── fund.py
│   │   ├── operation.py
│   │   ├── screenshot.py
│   │   └── nav.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py
│   │   ├── nav_service.py
│   │   ├── return_service.py
│   │   └── dedup_service.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── bloggers.py
│   │   ├── funds.py
│   │   ├── screenshots.py
│   │   ├── operations.py
│   │   ├── nav.py
│   │   └── returns.py
│   └── utils/
│       ├── __init__.py
│       ├── date_utils.py
│       └── validators.py
├── database/
│   └── schema.sql
├── tests/
├── config.py
├── requirements.txt
└── run.py
```

### 7.2 核心服务类

```python
# app/services/return_service.py
class ReturnService:
    def calculate_blogger_return(self, blogger_id, as_of_date):
        """计算博主收益"""
        pass
    
    def calculate_max_drawdown(self, blogger_id, from_date, to_date):
        """计算最大回撤"""
        pass
    
    def get_position_distribution(self, blogger_id, as_of_date):
        """获取持仓分布"""
        pass

# app/services/nav_service.py
class NAVService:
    def sync_nav_data(self, fund_ids=None, from_date=None):
        """同步净值数据"""
        pass
    
    def get_nav(self, fund_id, date):
        """获取指定日期净值"""
        pass
```

---

## 8. 部署方案

### 8.1 服务器要求

| 配置项 | 最低要求 | 推荐配置 |
|--------|---------|---------|
| CPU | 1核 | 2核 |
| 内存 | 1GB | 2GB |
| 存储 | 20GB | 50GB |
| 带宽 | 1Mbps | 5Mbps |

### 8.2 部署步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
mysql -u root -p < database/schema.sql

# 3. 启动 Umi-OCR
./Umi-OCR --host 127.0.0.1 --port 1224 &

# 4. 启动 Flask 应用
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# 5. 配置 Nginx
# 见 nginx.conf

# 6. 配置 Supervisor (进程守护)
# 见 supervisord.conf
```

### 8.3 定时任务

```bash
# crontab 配置

# 每日 18:00 同步净值数据
0 18 * * * curl -X POST http://localhost:5000/api/nav/sync

# 每周日凌晨 2:00 备份数据库
0 2 * * 0 mysqldump -u root -pPASSWORD fund_db > /backup/fund_db_$(date +\%Y\%m\%d).sql
```

---

## 9. 安全考虑

### 9.1 数据安全

- 定期备份 MySQL 数据库
- 截图文件存储加密(可选)
- 敏感配置信息(数据库密码等)使用环境变量

### 9.2 接口安全

- 文件上传限制(大小、类型)
- OCR 服务仅监听 localhost
- API 限流(防止滥用)

---

## 10. 性能优化

### 10.1 数据库优化

- 为常用查询字段添加索引
- 使用连接池
- 定期优化表

### 10.2 缓存策略

- 净值数据缓存(Redis 可选)
- 收益计算结果缓存(每日更新)

### 10.3 前端优化

- 图片压缩后上传
- 分页加载
- 懒加载图表

---

## 11. 监控与日志

### 11.1 日志配置

```python
# config.py
LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/fund2/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
}
```

### 11.2 监控指标

- OCR 识别成功率
- 净值同步成功率
- API 响应时间
- 数据库连接数

---

## 12. 测试计划

### 12.1 单元测试

- OCR 解析逻辑测试
- 收益计算算法测试
- 去重逻辑测试

### 12.2 集成测试

- 截图上传 → OCR → 解析 → 确认全流程
- 净值同步流程
- 收益计算流程

### 12.3 性能测试

- 100 个博主的收益计算耗时
- 批量上传 10 张截图的处理时间

---

## 13. 开发计划

### Phase 1: 基础架构 (1-2 周)
- [ ] 数据库设计与初始化
- [ ] Flask 项目骨架搭建
- [ ] 基本的博主、基金 CRUD API
- [ ] 前端框架搭建

### Phase 2: 核心功能 (2-3 周)
- [ ] Umi-OCR 集成
- [ ] 截图上传与解析
- [ ] 去重逻辑实现
- [ ] 收益计算算法实现
- [ ] 净值数据获取

### Phase 3: 前端界面 (2 周)
- [ ] 博主总览页
- [ ] 博主详情页
- [ ] 上传页面
- [ ] 历史记录页

### Phase 4: 优化与部署 (1 周)
- [ ] 性能优化
- [ ] 部署配置
- [ ] 监控与日志
- [ ] 文档完善

---

## 14. 待确认事项

- [ ] 前端框架选择(Vue 3 或 React)
- [ ] 是否需要 Redis 缓存(1C1G 服务器可能不够)
- [ ] 截图存储方案(本地或对象存储)
- [ ] 是否需要用户认证(当前设计为单用户)

---

## 附录

### A. 配置文件示例

```python
# config.py
class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'mysql://user:password@localhost/fund_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OCR 配置
    OCR_HOST = '127.0.0.1'
    OCR_PORT = 1224
    
    # 文件上传配置
    UPLOAD_FOLDER = '/var/www/fund2/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 净值 API 配置
    NAV_API_BASE = 'http://api.fund.eastmoney.com'
    NAV_API_TIMEOUT = 10
```

### B. requirements.txt

```
Flask==2.3.0
Flask-SQLAlchemy==3.0.0
Flask-Migrate==4.0.0
PyMySQL==1.1.0
requests==2.31.0
gunicorn==21.0.0
python-dotenv==1.0.0
```
