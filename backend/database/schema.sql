-- ============================================
-- 基金博主追踪系统 - 数据库架构
-- Database: fund_db
-- Charset: utf8mb4
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS fund_db 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE fund_db;

-- ============================================
-- 博主表 (bloggers)
-- ============================================
CREATE TABLE bloggers (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '博主ID',
    name VARCHAR(100) NOT NULL COMMENT '博主名称',
    sector VARCHAR(50) COMMENT '所属板块',
    observe_start_date DATE COMMENT '观察起始日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_sector (sector),
    INDEX idx_observe_date (observe_start_date),
    UNIQUE INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='博主表';

-- ============================================
-- 基金表 (funds)
-- ============================================
CREATE TABLE funds (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '基金ID',
    name VARCHAR(100) NOT NULL COMMENT '基金名称',
    fund_code VARCHAR(20) COMMENT '基金代码',
    fund_type VARCHAR(50) COMMENT '基金类型(股票型/混合型/债券型等)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE INDEX idx_fund_code (fund_code),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基金表';

-- ============================================
-- 初始持仓表 (initial_positions)
-- ============================================
CREATE TABLE initial_positions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    blogger_id INT NOT NULL COMMENT '博主ID',
    fund_id INT NOT NULL COMMENT '基金ID',
    shares DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '持有份额',
    cost_amount DECIMAL(18, 2) NOT NULL DEFAULT 0 COMMENT '成本金额',
    record_date DATE NOT NULL COMMENT '记录日期(观察起始日)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE,
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE RESTRICT,
    UNIQUE INDEX idx_blogger_fund_date (blogger_id, fund_id, record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='初始持仓表';

-- ============================================
-- 截图表 (screenshots)
-- ============================================
CREATE TABLE screenshots (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '截图ID',
    file_path VARCHAR(255) NOT NULL COMMENT '文件存储路径',
    file_name VARCHAR(255) COMMENT '原始文件名',
    operation_date DATE NOT NULL COMMENT '操作日期(用户选择)',
    ocr_raw_text TEXT COMMENT 'OCR原始识别文本',
    ocr_parsed_data JSON COMMENT '解析后的结构化数据',
    status ENUM('pending', 'confirmed', 'rejected', 'error') DEFAULT 'pending' COMMENT '处理状态',
    error_message TEXT COMMENT '错误信息',
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    processed_at DATETIME COMMENT '处理时间',
    
    INDEX idx_operation_date (operation_date),
    INDEX idx_status (status),
    INDEX idx_uploaded_at (uploaded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='截图表';

-- ============================================
-- 操作记录表 (operations)
-- ============================================
CREATE TABLE operations (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '操作ID',
    blogger_id INT NOT NULL COMMENT '博主ID',
    fund_id INT NOT NULL COMMENT '基金ID',
    operation_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('buy', 'sell') NOT NULL COMMENT '操作类型(买入/卖出)',
    amount DECIMAL(18, 2) COMMENT '金额(元)',
    shares DECIMAL(18, 4) COMMENT '份额',
    screenshot_id INT COMMENT '关联截图ID',
    notes TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE,
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE RESTRICT,
    FOREIGN KEY (screenshot_id) REFERENCES screenshots(id) ON DELETE SET NULL,
    INDEX idx_operation_date (operation_date),
    INDEX idx_blogger_date (blogger_id, operation_date),
    INDEX idx_fund_date (fund_id, operation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作记录表';

-- ============================================
-- 净值历史表 (nav_history)
-- ============================================
CREATE TABLE nav_history (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '净值记录ID',
    fund_id INT NOT NULL COMMENT '基金ID',
    nav_date DATE NOT NULL COMMENT '净值日期',
    nav DECIMAL(10, 4) NOT NULL COMMENT '单位净值',
    accumulated_nav DECIMAL(10, 4) COMMENT '累计净值',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_fund_date (fund_id, nav_date),
    INDEX idx_nav_date (nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='净值历史表';

-- ============================================
-- 持仓快照表 (position_snapshots)
-- 用于记录每日持仓状态,便于计算历史收益和回撤
-- ============================================
CREATE TABLE position_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '快照ID',
    blogger_id INT NOT NULL COMMENT '博主ID',
    fund_id INT NOT NULL COMMENT '基金ID',
    snapshot_date DATE NOT NULL COMMENT '快照日期',
    shares DECIMAL(18, 4) NOT NULL COMMENT '持有份额',
    cost_basis DECIMAL(18, 2) NOT NULL COMMENT '成本基础',
    market_value DECIMAL(18, 2) NOT NULL COMMENT '市值',
    nav DECIMAL(10, 4) NOT NULL COMMENT '当日净值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE,
    FOREIGN KEY (fund_id) REFERENCES funds(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_blogger_fund_date (blogger_id, fund_id, snapshot_date),
    INDEX idx_snapshot_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓快照表';

-- ============================================
-- 博主收益快照表 (blogger_return_snapshots)
-- 用于记录博主每日整体收益状态
-- ============================================
CREATE TABLE blogger_return_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '快照ID',
    blogger_id INT NOT NULL COMMENT '博主ID',
    snapshot_date DATE NOT NULL COMMENT '快照日期',
    total_cost DECIMAL(18, 2) NOT NULL COMMENT '总成本',
    total_market_value DECIMAL(18, 2) NOT NULL COMMENT '总市值',
    profit DECIMAL(18, 2) NOT NULL COMMENT '收益金额',
    return_rate DECIMAL(10, 6) NOT NULL COMMENT '收益率',
    max_drawdown DECIMAL(10, 6) COMMENT '最大回撤',
    observe_days INT NOT NULL COMMENT '观察天数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (blogger_id) REFERENCES bloggers(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_blogger_date (blogger_id, snapshot_date),
    INDEX idx_snapshot_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='博主收益快照表';

-- ============================================
-- 操作日志表 (operation_logs)
-- 用于审计和问题追溯
-- ============================================
CREATE TABLE operation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    table_name VARCHAR(50) NOT NULL COMMENT '表名',
    record_id INT NOT NULL COMMENT '记录ID',
    action ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL COMMENT '操作类型',
    old_data JSON COMMENT '旧数据',
    new_data JSON COMMENT '新数据',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_table_record (table_name, record_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- ============================================
-- 系统配置表 (system_config)
-- ============================================
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    config_key VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置说明',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- ============================================
-- 插入默认配置
-- ============================================
INSERT INTO system_config (config_key, config_value, description) VALUES
('min_observe_days', '30', '最小观察天数'),
('dedup_amount_threshold', '0.1', '去重金额差异阈值(10%)'),
('nav_sync_time', '18:00', '净值同步时间'),
('ocr_timeout', '10', 'OCR请求超时时间(秒)');

-- ============================================
-- 创建视图: 博主当前状态视图
-- ============================================
CREATE OR REPLACE VIEW v_blogger_status AS
SELECT 
    b.id AS blogger_id,
    b.name AS blogger_name,
    b.sector,
    b.observe_start_date,
    DATEDIFF(CURDATE(), b.observe_start_date) AS observe_days,
    CASE 
        WHEN b.observe_start_date IS NULL THEN 'inactive'
        WHEN DATEDIFF(CURDATE(), b.observe_start_date) < 30 THEN 'observing'
        ELSE 'active'
    END AS status,
    COALESCE(brs.total_cost, 0) AS total_cost,
    COALESCE(brs.total_market_value, 0) AS total_market_value,
    COALESCE(brs.profit, 0) AS profit,
    COALESCE(brs.return_rate, 0) AS return_rate,
    COALESCE(brs.max_drawdown, 0) AS max_drawdown
FROM bloggers b
LEFT JOIN blogger_return_snapshots brs 
    ON b.id = brs.blogger_id 
    AND brs.snapshot_date = CURDATE();

-- ============================================
-- 创建视图: 基金当前持仓视图
-- ============================================
CREATE OR REPLACE VIEW v_current_positions AS
SELECT 
    b.id AS blogger_id,
    b.name AS blogger_name,
    f.id AS fund_id,
    f.name AS fund_name,
    f.fund_code,
    ps.shares,
    ps.cost_basis,
    ps.market_value,
    ps.nav AS current_nav,
    (ps.market_value - ps.cost_basis) AS profit,
    CASE 
        WHEN ps.cost_basis > 0 THEN (ps.market_value - ps.cost_basis) / ps.cost_basis
        ELSE 0 
    END AS return_rate,
    ps.snapshot_date
FROM bloggers b
JOIN position_snapshots ps ON b.id = ps.blogger_id
JOIN funds f ON ps.fund_id = f.id
WHERE ps.snapshot_date = CURDATE();

-- ============================================
-- 创建存储过程: 计算博主收益
-- ============================================
DELIMITER //

CREATE PROCEDURE sp_calculate_blogger_return(
    IN p_blogger_id INT,
    IN p_as_of_date DATE
)
BEGIN
    DECLARE v_total_cost DECIMAL(18, 2) DEFAULT 0;
    DECLARE v_total_market_value DECIMAL(18, 2) DEFAULT 0;
    DECLARE v_profit DECIMAL(18, 2) DEFAULT 0;
    DECLARE v_return_rate DECIMAL(10, 6) DEFAULT 0;
    DECLARE v_observe_days INT DEFAULT 0;
    DECLARE v_observe_start_date DATE;
    
    -- 获取观察起始日
    SELECT observe_start_date INTO v_observe_start_date
    FROM bloggers WHERE id = p_blogger_id;
    
    SET v_observe_days = DATEDIFF(p_as_of_date, v_observe_start_date);
    
    -- 计算总成本和总市值
    SELECT 
        COALESCE(SUM(cost_basis), 0),
        COALESCE(SUM(market_value), 0)
    INTO v_total_cost, v_total_market_value
    FROM position_snapshots
    WHERE blogger_id = p_blogger_id
      AND snapshot_date = p_as_of_date;
    
    -- 计算收益
    SET v_profit = v_total_market_value - v_total_cost;
    SET v_return_rate = CASE WHEN v_total_cost > 0 
                             THEN v_profit / v_total_cost 
                             ELSE 0 END;
    
    -- 插入或更新快照
    INSERT INTO blogger_return_snapshots 
        (blogger_id, snapshot_date, total_cost, total_market_value, 
         profit, return_rate, observe_days)
    VALUES 
        (p_blogger_id, p_as_of_date, v_total_cost, v_total_market_value,
         v_profit, v_return_rate, v_observe_days)
    ON DUPLICATE KEY UPDATE
        total_cost = v_total_cost,
        total_market_value = v_total_market_value,
        profit = v_profit,
        return_rate = v_return_rate,
        observe_days = v_observe_days;
END //

DELIMITER ;

-- ============================================
-- 创建触发器: 操作记录变更日志
-- ============================================
DELIMITER //

CREATE TRIGGER tr_operations_after_insert
AFTER INSERT ON operations
FOR EACH ROW
BEGIN
    INSERT INTO operation_logs (table_name, record_id, action, new_data)
    VALUES ('operations', NEW.id, 'INSERT', JSON_OBJECT(
        'blogger_id', NEW.blogger_id,
        'fund_id', NEW.fund_id,
        'operation_date', NEW.operation_date,
        'operation_type', NEW.operation_type,
        'amount', NEW.amount,
        'shares', NEW.shares
    ));
END //

CREATE TRIGGER tr_operations_after_update
AFTER UPDATE ON operations
FOR EACH ROW
BEGIN
    INSERT INTO operation_logs (table_name, record_id, action, old_data, new_data)
    VALUES ('operations', NEW.id, 'UPDATE', 
        JSON_OBJECT(
            'blogger_id', OLD.blogger_id,
            'fund_id', OLD.fund_id,
            'operation_date', OLD.operation_date,
            'operation_type', OLD.operation_type,
            'amount', OLD.amount,
            'shares', OLD.shares
        ),
        JSON_OBJECT(
            'blogger_id', NEW.blogger_id,
            'fund_id', NEW.fund_id,
            'operation_date', NEW.operation_date,
            'operation_type', NEW.operation_type,
            'amount', NEW.amount,
            'shares', NEW.shares
        )
    );
END //

CREATE TRIGGER tr_operations_after_delete
AFTER DELETE ON operations
FOR EACH ROW
BEGIN
    INSERT INTO operation_logs (table_name, record_id, action, old_data)
    VALUES ('operations', OLD.id, 'DELETE', JSON_OBJECT(
        'blogger_id', OLD.blogger_id,
        'fund_id', OLD.fund_id,
        'operation_date', OLD.operation_date,
        'operation_type', OLD.operation_type,
        'amount', OLD.amount,
        'shares', OLD.shares
    ));
END //

DELIMITER ;

-- ============================================
-- 索引优化建议
-- ============================================
-- 对于大型数据集,可考虑添加以下索引:
-- ALTER TABLE operations ADD INDEX idx_blogger_fund_date (blogger_id, fund_id, operation_date);
-- ALTER TABLE nav_history ADD INDEX idx_date_nav (nav_date, nav);
