# OCR 字段提取逻辑设计

---

## 1. OCR 流程概述

### 1.1 整体流程

```
截图上传 → Umi-OCR识别 → 原始文本 → 字段解析 → 结构化数据 → 去重检测 → 人工确认
```

### 1.2 关键挑战

- 截图格式统一,但字段位置可能有偏移
- 操作金额可能是正数(买入)或负数(卖出)
- 博主名称可能在不同位置
- 需要识别字段标签和对应值

---

## 2. Umi-OCR 集成

### 2.1 HTTP API 调用

```python
import requests
import base64

class OCRExtractor:
    def __init__(self, host='127.0.0.1', port=1224):
        self.url = f'http://{host}:{port}/api/ocr'
    
    def recognize_image(self, image_path):
        """
        调用 Umi-OCR HTTP API
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            原始识别文本
        """
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            'base64': image_data,
            # 可选参数
            'language': 'chs',  # 简体中文
            'is_dense': True,   # 密集文本
        }
        
        response = requests.post(self.url, json=payload)
        result = response.json()
        
        if result.get('code') == 100:
            return result.get('data', '')
        else:
            raise Exception(f"OCR failed: {result.get('msg', 'Unknown error')}")
```

### 2.2 返回数据结构

Umi-OCR 返回格式:

```json
{
    "code": 100,
    "data": "识别出的文本内容...",
    "message": "success"
}
```

---

## 3. 字段解析逻辑

### 3.1 预期字段列表

根据需求,截图包含以下字段:

| 字段名 | 类型 | 示例 | 备注 |
|--------|------|------|------|
| 板块 | 文本 | "消费板块" | 可选 |
| 博主名称 | 文本 | "张三" | 必需 |
| 基金名称 | 文本 | "易方达消费行业股票" | 必需 |
| 操作 | 金额 | "+1000" 或 "-500" | 必需,正负表示买卖 |
| 持有收益金额 | 金额 | "123.45" | 平台数据,仅供参考 |
| 累计收益金额 | 金额 | "456.78" | 平台数据,仅供参考 |
| 近一年收益率 | 百分比 | "12.34%" | 平台数据,仅供参考 |
| 近三年收益率 | 百分比 | "45.67%" | 平台数据,仅供参考 |
| 最大回撤率 | 百分比 | "-8.90%" | 平台数据,仅供参考 |

### 3.2 文本解析策略

```python
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ExtractedRecord:
    """提取的记录"""
    blogger_name: str
    sector: Optional[str]
    fund_name: str
    operation: Optional[float]  # 正数买入,负数卖出
    holding_profit: Optional[float]
    total_profit: Optional[float]
    return_1y: Optional[float]
    return_3y: Optional[float]
    max_drawdown: Optional[float]
    raw_text: str


class ScreenshotParser:
    """截图文本解析器"""
    
    # 字段匹配正则表达式
    PATTERNS = {
        'sector': r'板块[：:]\s*([^\n]+)',
        'blogger': r'博主[名称]*[：:]\s*([^\n]+)',
        'fund_name': r'基金名称[：:]\s*([^\n]+)',
        'operation': r'操作[：:]\s*([+-]?\d+\.?\d*)',
        'holding_profit': r'持有收益[金额]*[：:]\s*([+-]?\d+\.?\d*)',
        'total_profit': r'累计收益[金额]*[：:]\s*([+-]?\d+\.?\d*)',
        'return_1y': r'近一年收益率[：:]\s*([+-]?\d+\.?\d*)%',
        'return_3y': r'近三年收益率[：:]\s*([+-]?\d+\.?\d*)%',
        'max_drawdown': r'最大回撤[率]*[：:]\s*([+-]?\d+\.?\d*)%',
    }
    
    def parse_text(self, raw_text: str) -> List[ExtractedRecord]:
        """
        解析 OCR 识别的文本
        
        Args:
            raw_text: OCR 原始文本
            
        Returns:
            提取的记录列表
        """
        records = []
        
        # 尝试提取所有字段
        extracted = {}
        for field, pattern in self.PATTERNS.items():
            match = re.search(pattern, raw_text)
            if match:
                extracted[field] = match.group(1).strip()
        
        # 构建记录
        record = ExtractedRecord(
            blogger_name=extracted.get('blogger', ''),
            sector=extracted.get('sector'),
            fund_name=extracted.get('fund_name', ''),
            operation=self._parse_amount(extracted.get('operation')),
            holding_profit=self._parse_amount(extracted.get('holding_profit')),
            total_profit=self._parse_amount(extracted.get('total_profit')),
            return_1y=self._parse_percentage(extracted.get('return_1y')),
            return_3y=self._parse_percentage(extracted.get('return_3y')),
            max_drawdown=self._parse_percentage(extracted.get('max_drawdown')),
            raw_text=raw_text
        )
        
        # 验证必需字段
        if record.blogger_name and record.fund_name:
            records.append(record)
        
        return records
    
    def _parse_amount(self, value: Optional[str]) -> Optional[float]:
        """解析金额"""
        if not value:
            return None
        try:
            return float(value.replace(',', ''))
        except ValueError:
            return None
    
    def _parse_percentage(self, value: Optional[str]) -> Optional[float]:
        """解析百分比"""
        if not value:
            return None
        try:
            return float(value) / 100  # 转换为小数
        except ValueError:
            return None
```

### 3.3 多记录处理

如果一张截图包含多个基金,需要按行分割:

```python
class MultiRecordParser(ScreenshotParser):
    """多记录截图解析器"""
    
    def parse_text(self, raw_text: str) -> List[ExtractedRecord]:
        """
        解析可能包含多个基金记录的文本
        """
        # 按空行或分隔符分割
        blocks = re.split(r'\n\s*\n', raw_text)
        
        records = []
        for block in blocks:
            if block.strip():
                record = self._parse_single_block(block)
                if record:
                    records.append(record)
        
        return records
    
    def _parse_single_block(self, block: str) -> Optional[ExtractedRecord]:
        """解析单个记录块"""
        # 使用父类方法解析
        results = super().parse_text(block)
        return results[0] if results else None
```

---

## 4. 去重检测逻辑

### 4.1 去重规则

```python
class DuplicateDetector:
    """重复记录检测器"""
    
    def detect_duplicates(self, record: ExtractedRecord, 
                          existing_records: List[dict],
                          threshold: float = 0.1) -> List[dict]:
        """
        检测疑似重复记录
        
        Args:
            record: 新提取的记录
            existing_records: 数据库中已存在的记录
            threshold: 金额差异阈值(默认10%)
            
        Returns:
            疑似重复的记录列表
        """
        duplicates = []
        
        for existing in existing_records:
            if self._is_duplicate(record, existing, threshold):
                duplicates.append(existing)
        
        return duplicates
    
    def _is_duplicate(self, new: ExtractedRecord, 
                      existing: dict, 
                      threshold: float) -> bool:
        """
        判断是否为重复记录
        
        规则:
        1. 同一博主
        2. 同一基金
        3. 同一日期(操作日期)
        4. 金额差异 < 10%
        """
        # 博主名称匹配(模糊匹配)
        if not self._fuzzy_match(new.blogger_name, existing['blogger_name']):
            return False
        
        # 基金名称匹配(模糊匹配)
        if not self._fuzzy_match(new.fund_name, existing['fund_name']):
            return False
        
        # 操作日期相同(外部传入)
        # 在调用时已经按日期过滤
        
        # 金额差异检查
        if new.operation and existing.get('amount'):
            diff = abs(new.operation - existing['amount']) / existing['amount']
            if diff < threshold:
                return True
        
        return True  # 如果没有金额,仅根据博主+基金+日期判断
    
    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.8) -> bool:
        """
        模糊字符串匹配
        
        使用简单的相似度计算(Levenshtein距离)
        """
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, str1, str2).ratio()
        return ratio >= threshold
```

### 4.2 去重流程

```python
def process_screenshot_with_dedup(
    image_path: str,
    operation_date: str,
    ocr_extractor: OCRExtractor,
    parser: ScreenshotParser,
    detector: DuplicateDetector
) -> dict:
    """
    处理截图并进行去重检测
    
    Returns:
        {
            'records': 提取的记录列表,
            'duplicates': {record_index: [疑似重复记录]},
            'raw_text': 原始OCR文本
        }
    """
    # 1. OCR识别
    raw_text = ocr_extractor.recognize_image(image_path)
    
    # 2. 字段解析
    records = parser.parse_text(raw_text)
    
    # 3. 去重检测
    duplicates = {}
    for i, record in enumerate(records):
        # 查询数据库中同一天同一博主的记录
        existing = query_existing_records(
            blogger_name=record.blogger_name,
            operation_date=operation_date
        )
        
        dup_records = detector.detect_duplicates(record, existing)
        if dup_records:
            duplicates[i] = dup_records
    
    return {
        'records': records,
        'duplicates': duplicates,
        'raw_text': raw_text
    }
```

---

## 5. 异常处理

### 5.1 OCR 识别失败

```python
class OCRException(Exception):
    """OCR识别异常"""
    pass

def safe_ocr_extract(extractor: OCRExtractor, image_path: str, retries: int = 3) -> str:
    """
    安全的OCR提取,支持重试
    """
    last_error = None
    
    for i in range(retries):
        try:
            return extractor.recognize_image(image_path)
        except Exception as e:
            last_error = e
            time.sleep(1)  # 等待后重试
    
    raise OCRException(f"OCR failed after {retries} retries: {last_error}")
```

### 5.2 字段解析失败

```python
class ParseException(Exception):
    """字段解析异常"""
    pass

def validate_record(record: ExtractedRecord) -> List[str]:
    """
    验证提取的记录
    
    Returns:
        错误信息列表,空列表表示验证通过
    """
    errors = []
    
    if not record.blogger_name:
        errors.append("博主名称缺失")
    
    if not record.fund_name:
        errors.append("基金名称缺失")
    
    if record.operation is None:
        errors.append("操作金额缺失")
    
    return errors
```

---

## 6. 批量处理

### 6.1 批量上传处理

```python
def process_batch_screenshots(
    image_paths: List[str],
    operation_date: str,
    ocr_extractor: OCRExtractor,
    parser: ScreenshotParser,
    detector: DuplicateDetector
) -> List[dict]:
    """
    批量处理截图
    
    Returns:
        每个截图的处理结果列表
    """
    results = []
    
    for image_path in image_paths:
        try:
            result = process_screenshot_with_dedup(
                image_path,
                operation_date,
                ocr_extractor,
                parser,
                detector
            )
            result['status'] = 'success'
            result['image_path'] = image_path
        except Exception as e:
            result = {
                'status': 'error',
                'error': str(e),
                'image_path': image_path
            }
        
        results.append(result)
    
    return results
```

---

## 7. 配置化字段映射

为了适应可能的截图格式变化,支持配置化字段映射:

```python
# config/ocr_fields.yaml
fields:
  - name: blogger_name
    label: "博主"
    pattern: "博主[名称]*[：:]\\s*([^\n]+)"
    required: true
    
  - name: fund_name
    label: "基金名称"
    pattern: "基金名称[：:]\\s*([^\n]+)"
    required: true
    
  - name: operation
    label: "操作"
    pattern: "操作[：:]\\s*([+-]?\\d+\\.?\\d*)"
    required: true
    type: "amount"
    
  - name: holding_profit
    label: "持有收益金额"
    pattern: "持有收益[金额]*[：:]\\s*([+-]?\\d+\\.?\\d*)"
    required: false
    type: "amount"
```

```python
import yaml

class ConfigurableParser(ScreenshotParser):
    """可配置的解析器"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.PATTERNS = self._build_patterns()
    
    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _build_patterns(self) -> dict:
        return {
            field['name']: field['pattern']
            for field in self.config['fields']
        }
```

---

## 8. 测试用例

### 8.1 单元测试

```python
import unittest

class TestScreenshotParser(unittest.TestCase):
    def setUp(self):
        self.parser = ScreenshotParser()
    
    def test_parse_simple_record(self):
        """测试简单记录解析"""
        text = """
        博主: 张三
        基金名称: 易方达消费行业股票
        操作: +1000
        """
        records = self.parser.parse_text(text)
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].blogger_name, '张三')
        self.assertEqual(records[0].fund_name, '易方达消费行业股票')
        self.assertEqual(records[0].operation, 1000.0)
    
    def test_parse_negative_operation(self):
        """测试卖出操作(负数)"""
        text = """
        博主: 李四
        基金名称: 华夏成长
        操作: -500
        """
        records = self.parser.parse_text(text)
        
        self.assertEqual(records[0].operation, -500.0)
    
    def test_parse_percentage(self):
        """测试百分比解析"""
        text = """
        博主: 王五
        基金名称: 南方优选成长
        操作: +2000
        近一年收益率: 15.6%
        """
        records = self.parser.parse_text(text)
        
        self.assertEqual(records[0].return_1y, 0.156)
```

---

## 9. 待实现功能

- [ ] 根据实际截图样本调整正则表达式
- [ ] 实现 OCR 结果缓存(避免重复识别)
- [ ] 添加图片预处理(提高识别准确率)
- [ ] 支持多种截图格式(通过配置切换)
