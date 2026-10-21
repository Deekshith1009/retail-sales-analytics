-- 03_business_analysis.sql  (MySQL 8.0+)
-- Business analysis queries for the Retail Sales & Profitability project.
-- Run ONE query at a time in MySQL Workbench: click inside it, press Ctrl+Enter.
-- Margin is always SUM(profit) / SUM(sales), never an average of row margins.
-- The dataset has no dates or Order IDs, so there are no time trends or order counts.

USE assessment;

-- =====================================================================
-- SECTION 0: SMALL DIMENSION TABLES (used by the join queries)
-- sales itself is NOT modified.
-- =====================================================================
DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_key  INT AUTO_INCREMENT PRIMARY KEY,
    category     VARCHAR(30) NOT NULL,
    sub_category VARCHAR(30) NOT NULL,
    UNIQUE KEY uq_product (category, sub_category)
);
INSERT INTO dim_product (category, sub_category)
SELECT DISTINCT category, sub_category
FROM sales
ORDER BY category, sub_category;

DROP TABLE IF EXISTS dim_geography;
CREATE TABLE dim_geography (
    geo_key INT AUTO_INCREMENT PRIMARY KEY,
    region  VARCHAR(10) NOT NULL,
    state   VARCHAR(40) NOT NULL,
    UNIQUE KEY uq_geo (region, state)
);
INSERT INTO dim_geography (region, state)
SELECT DISTINCT region, state
FROM sales
ORDER BY region, state;

-- Dimension checks
SELECT COUNT(*) AS product_rows FROM dim_product;
SELECT COUNT(*) AS geography_rows FROM dim_geography;
SELECT state, COUNT(DISTINCT region) AS regions_per_state
FROM sales GROUP BY state HAVING COUNT(DISTINCT region) > 1;

-- =====================================================================
-- Q1. OVERALL KPIs  (SELECT, aggregates)
-- =====================================================================
SELECT COUNT(*)                                   AS sales_lines,
       ROUND(SUM(sales), 2)                       AS total_sales,
       ROUND(SUM(profit), 2)                      AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct,
       SUM(quantity)                              AS total_quantity,
       SUM(loss_flag)                             AS loss_lines,
       ROUND(SUM(loss_flag) / COUNT(*) * 100, 2)  AS loss_line_pct,
       ROUND(AVG(sales), 2)                       AS avg_sales_per_line
FROM sales;

-- =====================================================================
-- Q2. CATEGORY PERFORMANCE  (GROUP BY, ORDER BY)
-- =====================================================================
SELECT category,
       COUNT(*)                                   AS sales_lines,
       ROUND(SUM(sales), 2)                       AS total_sales,
       ROUND(SUM(profit), 2)                      AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct
FROM sales
GROUP BY category
ORDER BY total_profit DESC;

-- =====================================================================
-- Q3. 10 LARGEST SINGLE-LINE LOSSES  (WHERE, ORDER BY, LIMIT)
-- =====================================================================
SELECT line_id, sub_category, state, discount, sales, quantity, profit
FROM sales
WHERE profit < 0
ORDER BY profit ASC
LIMIT 10;

-- =====================================================================
-- Q4. STATES WITH NEGATIVE TOTAL PROFIT AND AT LEAST 100 LINES  (GROUP BY, HAVING)
-- =====================================================================
SELECT state,
       COUNT(*)                                   AS sales_lines,
       ROUND(SUM(sales), 2)                       AS total_sales,
       ROUND(SUM(profit), 2)                      AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct
FROM sales
GROUP BY state
HAVING COUNT(*) >= 100 AND SUM(profit) < 0
ORDER BY total_profit ASC;

-- =====================================================================
-- Q5. PERFORMANCE BY DISCOUNT BAND  (CASE for ordering, aggregates)
-- =====================================================================
SELECT discount_band,
       COUNT(*)                                       AS sales_lines,
       ROUND(SUM(sales), 2)                           AS total_sales,
       ROUND(SUM(profit), 2)                          AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)       AS margin_pct,
       SUM(loss_flag)                                 AS loss_lines,
       ROUND(SUM(loss_flag) / COUNT(*) * 100, 2)      AS loss_line_pct
FROM sales
GROUP BY discount_band
ORDER BY CASE discount_band
             WHEN 'No Discount'     THEN 1
             WHEN 'Low (1-20%)'     THEN 2
             WHEN 'Medium (21-40%)' THEN 3
             ELSE 4
         END;

-- =====================================================================
-- Q6. SUB-CATEGORY PROFITABILITY LABELS  (CASE on aggregated results)
-- Thresholds (0% and 10%) are an analyst choice, not a company standard.
-- =====================================================================
SELECT sub_category,
       ROUND(SUM(sales), 2)                       AS total_sales,
       ROUND(SUM(profit), 2)                      AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct,
       CASE
           WHEN SUM(profit) < 0                       THEN 'Loss-making'
           WHEN SUM(profit) / SUM(sales) < 0.10       THEN 'Low margin (<10%)'
           ELSE 'Healthy margin (>=10%)'
       END                                        AS profitability_label
FROM sales
GROUP BY sub_category
ORDER BY margin_pct ASC;

-- =====================================================================
-- Q7. JOIN: SUB-CATEGORY PERFORMANCE WITH ITS CATEGORY  (INNER JOIN)
-- =====================================================================
SELECT p.category,
       p.sub_category,
       COUNT(*)                                   AS sales_lines,
       ROUND(SUM(s.sales), 2)                     AS total_sales,
       ROUND(SUM(s.profit), 2)                    AS total_profit,
       ROUND(SUM(s.profit) / SUM(s.sales) * 100, 2) AS margin_pct
FROM sales AS s
INNER JOIN dim_product AS p
        ON s.category = p.category
       AND s.sub_category = p.sub_category
GROUP BY p.category, p.sub_category
ORDER BY p.category, total_profit DESC;

-- =====================================================================
-- Q8. JOIN: REGION AND STATE PERFORMANCE  (INNER JOIN, 3 columns of grouping)
-- =====================================================================
SELECT g.region,
       g.state,
       COUNT(*)                                   AS sales_lines,
       ROUND(SUM(s.profit), 2)                    AS total_profit,
       ROUND(SUM(s.profit) / SUM(s.sales) * 100, 2) AS margin_pct
FROM sales AS s
INNER JOIN dim_geography AS g
        ON s.region = g.region
       AND s.state = g.state
GROUP BY g.region, g.state
ORDER BY g.region, total_profit DESC;

-- =====================================================================
-- Q9. LEFT JOIN ANTI-PATTERN: SUB-CATEGORIES WITH NO LOSS-MAKING LINES
-- =====================================================================
SELECT p.category, p.sub_category
FROM dim_product AS p
LEFT JOIN (
    SELECT DISTINCT category, sub_category
    FROM sales
    WHERE profit < 0
) AS losers
       ON p.category = losers.category
      AND p.sub_category = losers.sub_category
WHERE losers.sub_category IS NULL
ORDER BY p.category, p.sub_category;

-- =====================================================================
-- Q10. SUBQUERY: SUB-CATEGORIES WITH A MARGIN BELOW THE COMPANY MARGIN
-- =====================================================================
SELECT sub_category,
       ROUND(SUM(profit) / SUM(sales) * 100, 2) AS margin_pct,
       ROUND((SELECT SUM(profit) / SUM(sales) * 100 FROM sales), 2) AS overall_margin_pct
FROM sales
GROUP BY sub_category
HAVING SUM(profit) / SUM(sales) < (SELECT SUM(profit) / SUM(sales) FROM sales)
ORDER BY margin_pct ASC;

-- =====================================================================
-- Q11. SUBQUERY: STATES WHOSE TOTAL PROFIT IS BELOW THE AVERAGE STATE PROFIT
-- =====================================================================
SELECT state,
       ROUND(SUM(profit), 2) AS total_profit,
       ROUND((SELECT AVG(state_profit)
              FROM (SELECT SUM(profit) AS state_profit FROM sales GROUP BY state) AS t), 2)
                             AS average_state_profit
FROM sales
GROUP BY state
HAVING SUM(profit) < (SELECT AVG(state_profit)
                      FROM (SELECT SUM(profit) AS state_profit FROM sales GROUP BY state) AS t)
ORDER BY total_profit ASC;

-- =====================================================================
-- Q12. CTE: WHERE IS THE MONEY LOST? (gross loss and share by sub-category)
-- =====================================================================
WITH losses AS (
    SELECT sub_category,
           COUNT(*)                AS loss_lines,
           ROUND(SUM(profit), 2)   AS gross_loss
    FROM sales
    WHERE profit < 0
    GROUP BY sub_category
)
SELECT sub_category,
       loss_lines,
       gross_loss,
       ROUND(gross_loss / (SELECT SUM(gross_loss) FROM losses) * 100, 2) AS share_of_all_losses_pct
FROM losses
ORDER BY gross_loss ASC;

-- =====================================================================
-- Q13. CTE: REGION x DISCOUNT BAND (margin and share of each region's lines)
-- =====================================================================
WITH region_band AS (
    SELECT region,
           discount_band,
           COUNT(*)                                 AS sales_lines,
           ROUND(SUM(profit) / SUM(sales) * 100, 2) AS margin_pct
    FROM sales
    GROUP BY region, discount_band
),
region_totals AS (
    SELECT region, SUM(sales_lines) AS region_lines
    FROM region_band
    GROUP BY region
)
SELECT b.region,
       b.discount_band,
       b.sales_lines,
       ROUND(b.sales_lines / t.region_lines * 100, 1) AS share_of_region_lines_pct,
       b.margin_pct
FROM region_band AS b
JOIN region_totals AS t ON b.region = t.region
ORDER BY b.region,
         CASE b.discount_band
             WHEN 'No Discount'     THEN 1
             WHEN 'Low (1-20%)'     THEN 2
             WHEN 'Medium (21-40%)' THEN 3
             ELSE 4
         END;

-- =====================================================================
-- Q14. WINDOW RANK(): RANK SUB-CATEGORIES BY PROFIT WITHIN EACH CATEGORY
-- =====================================================================
WITH sub AS (
    SELECT category, sub_category,
           ROUND(SUM(profit), 2) AS total_profit
    FROM sales
    GROUP BY category, sub_category
)
SELECT category,
       sub_category,
       total_profit,
       RANK() OVER (PARTITION BY category ORDER BY total_profit DESC) AS rank_in_category
FROM sub
ORDER BY category, rank_in_category;

-- =====================================================================
-- Q15. WINDOW DENSE_RANK(): STATES RANKED BY MARGIN (states with >= 100 lines)
-- =====================================================================
WITH st AS (
    SELECT state,
           COUNT(*)                                   AS sales_lines,
           ROUND(SUM(profit), 2)                      AS total_profit,
           ROUND(SUM(profit) / SUM(sales) * 100, 2)   AS margin_pct
    FROM sales
    GROUP BY state
    HAVING COUNT(*) >= 100
)
SELECT state, sales_lines, total_profit, margin_pct,
       DENSE_RANK() OVER (ORDER BY margin_pct DESC) AS margin_rank
FROM st
ORDER BY margin_rank, state;

-- =====================================================================
-- Q16. WINDOW RUNNING TOTAL: CUMULATIVE SHARE OF PROFIT (Pareto view)
-- Sub-categories ordered by profit, highest first.
-- =====================================================================
WITH sub AS (
    SELECT sub_category, SUM(profit) AS total_profit
    FROM sales
    GROUP BY sub_category
)
SELECT sub_category,
       ROUND(total_profit, 2) AS total_profit,
       ROUND(SUM(total_profit) OVER (ORDER BY total_profit DESC
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)
                              AS running_profit,
       ROUND(SUM(total_profit) OVER (ORDER BY total_profit DESC
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(total_profit) OVER () * 100, 2)
                              AS running_pct_of_total_profit
FROM sub
ORDER BY total_profit DESC;

-- =====================================================================
-- Q17. WINDOW PERCENT OF TOTAL: SHARE OF SALES AND PROFIT BY SUB-CATEGORY
-- =====================================================================
WITH sub AS (
    SELECT sub_category,
           SUM(sales)  AS total_sales,
           SUM(profit) AS total_profit
    FROM sales
    GROUP BY sub_category
)
SELECT sub_category,
       ROUND(total_sales, 2)                                  AS total_sales,
       ROUND(total_sales  / SUM(total_sales)  OVER () * 100, 2) AS pct_of_total_sales,
       ROUND(total_profit, 2)                                 AS total_profit,
       ROUND(total_profit / SUM(total_profit) OVER () * 100, 2) AS pct_of_total_profit
FROM sub
ORDER BY total_sales DESC;

-- =====================================================================
-- Q18. WINDOW LAG(): PROFIT GAP TO THE NEXT-BETTER SUB-CATEGORY
-- No dates exist, so LAG is applied to a ranking, not to time.
-- =====================================================================
WITH sub AS (
    SELECT sub_category, SUM(profit) AS total_profit
    FROM sales
    GROUP BY sub_category
)
SELECT sub_category,
       ROUND(total_profit, 2) AS total_profit,
       ROUND(LAG(total_profit) OVER (ORDER BY total_profit DESC), 2) AS profit_of_next_better,
       ROUND(LAG(total_profit) OVER (ORDER BY total_profit DESC) - total_profit, 2)
                              AS gap_to_next_better
FROM sub
ORDER BY total_profit DESC;

-- =====================================================================
-- Q19. WINDOW NTILE(4): STATE PROFIT QUARTILES
-- Quartile 1 = highest-profit group of states, quartile 4 = lowest.
-- =====================================================================
WITH st AS (
    SELECT state, SUM(profit) AS total_profit, SUM(sales) AS total_sales
    FROM sales
    GROUP BY state
)
SELECT q                                              AS profit_quartile,
       COUNT(*)                                       AS states_in_quartile,
       ROUND(SUM(total_profit), 2)                    AS quartile_profit,
       ROUND(SUM(total_profit) / SUM(total_sales) * 100, 2) AS quartile_margin_pct
FROM (
    SELECT state, total_profit, total_sales,
           NTILE(4) OVER (ORDER BY total_profit DESC) AS q
    FROM st
) AS ranked
GROUP BY q
ORDER BY q;

-- =====================================================================
-- Q20. EXACT DISCOUNT LEVEL ANALYSIS  (GROUP BY on discount)
-- Check sales_lines before trusting a level's margin: small groups are unreliable.
-- =====================================================================
SELECT discount,
       COUNT(*)                                       AS sales_lines,
       ROUND(SUM(sales), 2)                           AS total_sales,
       ROUND(SUM(profit), 2)                          AS total_profit,
       ROUND(SUM(profit) / SUM(sales) * 100, 2)       AS margin_pct,
       ROUND(SUM(loss_flag) / COUNT(*) * 100, 2)      AS loss_line_pct
FROM sales
GROUP BY discount
ORDER BY discount;

-- =====================================================================
-- Q21. RECONCILIATION: EVERY SUMMARY MUST ADD BACK TO THE BASELINE
-- =====================================================================
WITH sub AS (
    SELECT sub_category, SUM(sales) AS s, SUM(profit) AS p
    FROM sales
    GROUP BY sub_category
)
SELECT ROUND(SUM(s), 4) AS sales_from_summary,
       ROUND(SUM(p), 4) AS profit_from_summary,
       CASE WHEN ABS(SUM(s) - 2297200.8603) < 0.01
             AND ABS(SUM(p) - 286397.0217)  < 0.01
            THEN 'PASS' ELSE 'FAIL' END AS status
FROM sub;