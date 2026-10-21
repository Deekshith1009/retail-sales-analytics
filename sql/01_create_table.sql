-- 01_create_table.sql  (MySQL 8.0+)
-- Creates the database and sales table for the cleaned Superstore data.
-- Source: data/processed/superstore_clean.csv (17 columns, 9,994 rows)

CREATE DATABASE IF NOT EXISTS retail_analytics
    CHARACTER SET utf8mb4;
USE assessment;

DROP TABLE IF EXISTS sales;

CREATE TABLE sales (
    line_id        INT             NOT NULL,             -- surrogate row number, NOT an Order ID
    ship_mode      VARCHAR(20)     NOT NULL,
    segment        VARCHAR(20)     NOT NULL,
    country        VARCHAR(30)     NOT NULL,
    city           VARCHAR(60)     NOT NULL,
    state          VARCHAR(40)     NOT NULL,
    postal_code    CHAR(5)         NOT NULL,             -- text, keeps leading zeros
    region         VARCHAR(10)     NOT NULL,
    category       VARCHAR(30)     NOT NULL,
    sub_category   VARCHAR(30)     NOT NULL,
    sales          DECIMAL(14,6)   NOT NULL,             -- exact decimals, no float rounding
    quantity       INT             NOT NULL,
    discount       DECIMAL(4,2)    NOT NULL,             -- fraction: 0.00 to 1.00
    profit         DECIMAL(14,6)   NOT NULL,             -- negatives are valid losses
    loss_flag      TINYINT         NOT NULL,
    discount_band  VARCHAR(20)     NOT NULL,
    profit_margin  DECIMAL(10,4)   NULL,                 -- row-level only; for groups use SUM(profit)/SUM(sales)

    PRIMARY KEY (line_id),

    CONSTRAINT chk_sales_positive    CHECK (sales > 0),
    CONSTRAINT chk_quantity_positive CHECK (quantity >= 1),
    CONSTRAINT chk_discount_range    CHECK (discount BETWEEN 0 AND 1),
    CONSTRAINT chk_loss_flag         CHECK (loss_flag IN (0, 1)),
    CONSTRAINT chk_postal_code       CHECK (postal_code REGEXP '^[0-9]{5}$'),
    CONSTRAINT chk_discount_band     CHECK (discount_band IN
        ('No Discount', 'Low (1-20%)', 'Medium (21-40%)', 'High (>40%)'))
);