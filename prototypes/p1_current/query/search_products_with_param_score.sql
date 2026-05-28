# Example input:
SET @q = 'Кеды Vans Sk8-Hi M191 Кроссовки с усиленным мысом и пяткой дольше сохраняют форму. Упругая подошва снижает ударную нагрузку на стопу.';
SET @p1_name = NULL;
SET @p1_value = NULL;
SET @p2_name = NULL;
SET @p2_value = NULL;
SET @p3_name = NULL;
SET @p3_value = NULL;

# SET @p1_name = 'Цвет';
# SET @p1_value = 'белый';
# SET @p2_name = 'Сезон';
# SET @p2_value = 'весна-осень';

WITH requested_params AS (
    SELECT @p1_name AS param_name, @p1_value AS param_value
    UNION ALL
    SELECT @p2_name, @p2_value
    UNION ALL
    SELECT @p3_name, @p3_value
),
product_param_score AS (
    SELECT
        p.offer_id,
        COALESCE(
            SUM(
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM product_attributes pa
                        WHERE pa.offer_id = p.offer_id
                          AND pa.name = np.param_name
                          AND pa.value LIKE CONCAT('%', np.param_value, '%')
                    )
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ) AS param_score
    FROM products p
    LEFT JOIN requested_params np ON TRUE
    GROUP BY p.offer_id
),
product_text_score AS (
    SELECT
        p.offer_id,
        MATCH(p.name, p.description) AGAINST(@q IN NATURAL LANGUAGE MODE) AS text_score
    FROM products p
)
SELECT
    p.offer_id,
    p.name,
    p.description,
    pts.text_score,
    pps.param_score
FROM products p
JOIN product_param_score pps ON pps.offer_id = p.offer_id
JOIN product_text_score pts ON pts.offer_id = p.offer_id
WHERE pts.text_score > 0
   OR pps.param_score > 0
ORDER BY pps.param_score DESC, pts.text_score DESC
LIMIT 20;
