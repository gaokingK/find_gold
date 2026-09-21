# 收益计算算法设计

---

## 1. 核心概念

### 1.1 基本定义

- **成本基础 (Cost Basis)**: 累计投入资金(买入金额总和 - 卖出金额总和)
- **市值 (Market Value)**: 当前持有份额 × 当前净值
- **收益 (Profit)**: 市值 - 成本基础
- **收益率 (Return Rate)**: 收益 / 成本基础

### 1.2 计算原则

1. **时间加权**: 以观察起始日为基准,只计算观察期间的收益
2. **净值驱动**: 通过净值变化计算市值,不依赖平台提供的收益数据
3. **逐日清算**: 每日记录持仓快照,便于计算历史回撤

---

## 2. 收益计算算法

### 2.1 持仓计算逻辑

```python
def calculate_position(blogger_id, fund_id, as_of_date):
    """
    计算指定日期的持仓情况
    
    Returns:
        shares: 持有份额
        cost_basis: 成本基础
    """
    # 1. 获取初始持仓
    initial = get_initial_position(blogger_id, fund_id)
    shares = initial.shares if initial else 0
    cost_basis = initial.cost_amount if initial else 0
    
    # 2. 获取观察期间的所有操作记录
    operations = get_operations(
        blogger_id, 
        fund_id, 
        from_date=observe_start_date,
        to_date=as_of_date
    )
    
    # 3. 逐笔处理操作
    for op in operations:
        if op.operation_type == 'buy':
            # 买入: 增加份额和成本
            if op.shares:
                shares += op.shares
            else:
                # 金额买入,需要根据当日净值计算份额
                nav = get_nav(fund_id, op.operation_date)
                shares += op.amount / nav
            cost_basis += op.amount or (op.shares * get_nav(fund_id, op.operation_date))
            
        elif op.operation_type == 'sell':
            # 卖出: 减少份额和成本(按比例)
            if op.shares:
                sell_shares = op.shares
            else:
                # 金额卖出,需要根据当日净值计算份额
                nav = get_nav(fund_id, op.operation_date)
                sell_shares = op.amount / nav
            
            # 按比例减少成本基础
            cost_reduction = cost_basis * (sell_shares / shares)
            shares -= sell_shares
            cost_basis -= cost_reduction
    
    return shares, cost_basis
```

### 2.2 收益率计算

```python
def calculate_return(blogger_id, as_of_date):
    """
    计算博主的整体收益率
    
    Returns:
        total_cost: 总成本基础
        total_market_value: 总市值
        profit: 收益金额
        return_rate: 收益率
    """
    # 1. 获取博主持有的所有基金
    funds = get_blogger_funds(blogger_id)
    
    total_cost = 0
    total_market_value = 0
    
    for fund_id in funds:
        # 2. 计算每个基金的持仓
        shares, cost_basis = calculate_position(blogger_id, fund_id, as_of_date)
        
        # 3. 获取当前净值
        current_nav = get_nav(fund_id, as_of_date)
        
        # 4. 计算市值
        market_value = shares * current_nav
        
        total_cost += cost_basis
        total_market_value += market_value
    
    # 5. 计算收益
    profit = total_market_value - total_cost
    return_rate = profit / total_cost if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'total_market_value': total_market_value,
        'profit': profit,
        'return_rate': return_rate
    }
```

### 2.3 最大回撤计算

```python
def calculate_max_drawdown(blogger_id, from_date, to_date):
    """
    计算最大回撤
    
    算法:
    1. 获取每日市值序列
    2. 计算每个时点到后续最高点的回撤
    3. 返回最大回撤值
    """
    # 1. 获取每日市值快照
    daily_values = get_daily_market_values(blogger_id, from_date, to_date)
    
    # 2. 计算最大回撤
    peak = 0
    max_drawdown = 0
    max_drawdown_date = None
    
    for date, value in daily_values:
        if value > peak:
            peak = value
        
        drawdown = (peak - value) / peak if peak > 0 else 0
        
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_date = date
    
    return {
        'max_drawdown': max_drawdown,
        'max_drawdown_date': max_drawdown_date,
        'peak_value': peak
    }
```

---

## 3. 持仓快照策略

### 3.1 快照生成时机

- **每日收盘后**: 根据当日操作和净值更新快照
- **操作发生时**: 立即更新快照

### 3.2 快照计算

```python
def generate_daily_snapshot(blogger_id, snapshot_date):
    """
    生成每日持仓快照
    """
    funds = get_blogger_funds(blogger_id)
    
    for fund_id in funds:
        shares, cost_basis = calculate_position(blogger_id, fund_id, snapshot_date)
        nav = get_nav(fund_id, snapshot_date)
        market_value = shares * nav
        
        save_position_snapshot(
            blogger_id=blogger_id,
            fund_id=fund_id,
            snapshot_date=snapshot_date,
            shares=shares,
            cost_basis=cost_basis,
            market_value=market_value
        )
```

---

## 4. 观察期判断

```python
def get_blogger_status(blogger_id, as_of_date):
    """
    判断博主状态
    
    Returns:
        status: 'active' | 'observing' | 'inactive'
        observe_days: 观察天数
    """
    blogger = get_blogger(blogger_id)
    observe_start = blogger.observe_start_date
    
    if not observe_start:
        return 'inactive', 0
    
    observe_days = (as_of_date - observe_start).days
    
    if observe_days < 30:
        return 'observing', observe_days
    else:
        return 'active', observe_days
```

---

## 5. 持仓分布计算

```python
def calculate_position_distribution(blogger_id, as_of_date):
    """
    计算持仓分布
    
    Returns:
        List of {fund_name, market_value, percentage}
    """
    funds = get_blogger_funds(blogger_id)
    
    positions = []
    total_value = 0
    
    for fund_id in funds:
        shares, _ = calculate_position(blogger_id, fund_id, as_of_date)
        nav = get_nav(fund_id, as_of_date)
        market_value = shares * nav
        
        positions.append({
            'fund_id': fund_id,
            'fund_name': get_fund_name(fund_id),
            'shares': shares,
            'market_value': market_value
        })
        total_value += market_value
    
    # 计算百分比
    for pos in positions:
        pos['percentage'] = pos['market_value'] / total_value if total_value > 0 else 0
    
    return sorted(positions, key=lambda x: x['market_value'], reverse=True)
```

---

## 6. 操作频率统计

```python
def calculate_operation_frequency(blogger_id, from_date, to_date):
    """
    计算操作频率
    
    Returns:
        monthly: 按月统计
        quarterly: 按季度统计
    """
    operations = get_operations(blogger_id, from_date, to_date)
    
    # 按月统计
    monthly = {}
    for op in operations:
        month_key = op.operation_date.strftime('%Y-%m')
        monthly[month_key] = monthly.get(month_key, 0) + 1
    
    # 按季度统计
    quarterly = {}
    for op in operations:
        quarter_key = f"{op.operation_date.year}-Q{(op.operation_date.month - 1) // 3 + 1}"
        quarterly[quarter_key] = quarterly.get(quarter_key, 0) + 1
    
    return {
        'monthly': monthly,
        'quarterly': quarterly,
        'total_operations': len(operations)
    }
```

---

## 7. 边界情况处理

### 7.1 净值缺失

- **场景**: 某日净值数据未获取
- **处理**: 使用最近一个交易日的净值

```python
def get_nav_with_fallback(fund_id, target_date):
    """
    获取净值,支持回退到最近交易日
    """
    nav = get_nav(fund_id, target_date)
    if nav:
        return nav
    
    # 回退到最近交易日(最多回退 5 天)
    for i in range(1, 6):
        fallback_date = target_date - timedelta(days=i)
        nav = get_nav(fund_id, fallback_date)
        if nav:
            return nav
    
    raise ValueError(f"No NAV data found for fund {fund_id} near {target_date}")
```

### 7.2 份额为负

- **场景**: 卖出份额超过持有份额
- **处理**: 拒绝操作,提示用户确认

### 7.3 成本基础为零

- **场景**: 所有持仓已卖出
- **处理**: 收益率显示为 N/A 或 0

---

## 8. 性能优化

### 8.1 快照缓存

- 每日快照避免重复计算
- 查询时直接使用快照数据

### 8.2 增量更新

- 操作变更时,只更新受影响的快照
- 避免全量重新计算

### 8.3 批量净值获取

- 一次性获取多个基金的净值
- 减少外部 API 调用次数
