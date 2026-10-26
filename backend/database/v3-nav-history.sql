CREATE TABLE IF NOT EXISTS nav_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fund_id INT NOT NULL,
    nav_date DATE NOT NULL,
    nav DECIMAL(18, 4) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_nav_history_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    UNIQUE INDEX uk_nav_history_fund_date (
        fund_id, nav_date
    ),
    INDEX idx_nav_history_date (nav_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;