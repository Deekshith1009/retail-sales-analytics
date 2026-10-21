-- 02_data_validation.sql  (MySQL 8.0+)
-- Confirms the database matches the baseline from Phase 1 (Python) and Phase 2 (Excel).
USE retail_analytics;

-- 1. RECONCILIATION AGAINST THE BASELINE (every row should say PASS)
SELECT 'Row count' AS metric,
       COUNT(*) AS actual,
       9994 AS expected,
       CASE WHEN COUNT(*) = 9994 THEN 'PASS' ELSE 'FAIL' END AS status
FROM sales
UNION ALL
SELECT 'Total sales', SUM(sales), 2297200.8603,
       CASE WHEN ABS(SUM(sales) - 2297200.8603) < 0.01 THEN 'PASS' ELSE 'FAIL' END
FROM sales
UNION ALL
SELECT 'Total profit', SUM(profit), 286397.0217,
       CASE WHEN ABS(SUM(profit) - 286397.0217) < 0.01 THEN 'PASS' ELSE 'FAIL' END
FROM sales
UNION ALL
SELECT 'Total quantity', SUM(quantity), 37873,
       CASE WHEN SUM(quantity) = 37873 THEN 'PASS' ELSE 'FAIL' END
FROM sales
UNION ALL
SELECT 'Loss-making lines', SUM(loss_flag), 1871,
       CASE WHEN SUM(loss_flag) = 1871 THEN 'PASS' ELSE 'FAIL' END
FROM sales;

-- 2. BLANK TEXT VALUES (expect 0 everywhere)
SELECT
    SUM(CASE WHEN TRIM(ship_mode) = ''    THEN 1 ELSE 0 END) AS blank_ship_mode,
    SUM(CASE WHEN TRIM(segment) = ''      THEN 1 ELSE 0 END) AS blank_segment,
    SUM(CASE WHEN TRIM(city) = ''         THEN 1 ELSE 0 END) AS blank_city,
    SUM(CASE WHEN TRIM(state) = ''        THEN 1 ELSE 0 END) AS blank_state,
    SUM(CASE WHEN TRIM(region) = ''       THEN 1 ELSE 0 END) AS blank_region,
    SUM(CASE WHEN TRIM(category) = ''     THEN 1 ELSE 0 END) AS blank_category,
    SUM(CASE WHEN TRIM(sub_category) = '' THEN 1 ELSE 0 END) AS blank_sub_category
FROM sales;

-- 3. POSTAL CODES (expect 0 invalid; 449 begin with a zero)
SELECT
    SUM(CASE WHEN postal_code NOT REGEXP '^[0-9]{5}$' THEN 1 ELSE 0 END) AS invalid_postal_codes,
    SUM(CASE WHEN postal_code LIKE '0%'               THEN 1 ELSE 0 END) AS codes_starting_with_zero
FROM sales;

-- 4. DISTINCT VALUE COUNTS (expect 4, 3, 4, 3, 17, 49)
SELECT
    COUNT(DISTINCT ship_mode)    AS ship_modes,
    COUNT(DISTINCT segment)      AS segments,
    COUNT(DISTINCT region)       AS regions,
    COUNT(DISTINCT category)     AS categories,
    COUNT(DISTINCT sub_category) AS sub_categories,
    COUNT(DISTINCT state)        AS states
FROM sales;

-- 5. DISCOUNT BAND COUNTS (expect 4798 / 3803 / 460 / 933)
SELECT discount_band, COUNT(*) AS line_count
FROM sales
GROUP BY discount_band
ORDER BY MIN(discount);

-- 6. BAND AND LOSS-FLAG CONSISTENCY (both expect 0)
SELECT
    SUM(CASE WHEN (profit < 0) <> (loss_flag = 1) THEN 1 ELSE 0 END) AS loss_flag_mismatches,
    SUM(CASE WHEN discount_band <>
            CASE WHEN discount = 0    THEN 'No Discount'
                 WHEN discount <= 0.20 THEN 'Low (1-20%)'
                 WHEN discount <= 0.40 THEN 'Medium (21-40%)'
                 ELSE 'High (>40%)' END
        THEN 1 ELSE 0 END) AS band_mismatches
FROM sales;

-- 7. IDENTICAL ROWS (expect 17 extra copies; kept, as documented in Phase 3)
SELECT COALESCE(SUM(copies - 1), 0) AS extra_copies
FROM (
    SELECT COUNT(*) AS copies
    FROM sales
    GROUP BY ship_mode, segment, country, city, state, postal_code, region,
             category, sub_category, sales, quantity, discount, profit
    HAVING COUNT(*) > 1
) AS duplicate_groups;

-- 8. CATEGORY TOTALS (compare with the Excel pivot and the Python output)
SELECT category,
       COUNT(*)                                   AS line_count,
       ROUND(SUM(sales), 2)                       AS total_sales,
       ROUND(SUM(profit), 2)                      AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct
FROM sales
GROUP BY category
ORDER BY total_profit DESC;