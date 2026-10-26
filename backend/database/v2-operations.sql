CREATE TABLE IF NOT EXISTS operations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blogger_id INT NOT NULL,
    fund_id INT NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    operation_date DATE NOT NULL,
    shares DECIMAL(18, 4) NOT NULL DEFAULT 0,
    amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    remark VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_operations_blogger
        FOREIGN KEY (blogger_id) REFERENCES bloggers(id),
    CONSTRAINT fk_operations_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    INDEX idx_operations_blogger_date(
        blogger_id, operation_date
    ),
    INDEX idx_operations_fund_date(
        fund_id, operation_date
    ),
    INDEX idx_operations_type (operation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;