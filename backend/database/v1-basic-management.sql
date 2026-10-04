CREATE TABLE IF NOT EXISTS bloggers(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50) NOT NULL,
    observe_start_date DATE NOT NULL,
    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_bloggers_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS funds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    fund_code VARCHAR(20) NOT NULL,
    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_funds_code (fund_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS initial_positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    blogger_id INT NOT NULL,
    fund_id INT NOT NULL,
    shares DECIMAL(18, 4) NOT NULL DEFAULT 0,
    cost_amount DECIMAL(18, 2) NOT NULL DEFAULT 0,
    record_date DATE NOT NULL,
    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_initial_positions_blogger
        FOREIGN KEY (blogger_id) REFERENCES bloggers(id),
    CONSTRAINT fk_initial_positions_fund
        FOREIGN KEY (fund_id) REFERENCES funds(id),
    UNIQUE INDEX fk_initial_positions_unique (
        blogger_id, fund_id, record_date
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;