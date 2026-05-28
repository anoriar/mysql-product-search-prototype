# Пример входных данных:
SET @q = 'Кеды Vans Sk8-Hi M191 Кроссовки с усиленным мысом и пяткой дольше сохраняют форму. Упругая подошва снижает ударную нагрузку на стопу.';
SET @p1_name = 'Цвет';
SET @p1_value = 'бел';
SET @p2_name = 'Материал';
SET @p2_value = 'кожа';
SET @p3_name = NULL;
SET @p3_value = NULL;
#
# Логика param_score:
# +1 за каждый заданный параметр, если у товара есть запись в product_attributes,
# где pa.name = param_name и pa.value LIKE CONCAT('%', param_value, '%').

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
                    WHEN np.param_name IS NOT NULL AND EXISTS (
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
    pps.param_score,
    (pts.text_score + pps.param_score) AS score
FROM products p
JOIN product_param_score pps ON pps.offer_id = p.offer_id
JOIN product_text_score pts ON pts.offer_id = p.offer_id
WHERE pts.text_score > 0
   OR pps.param_score > 0
ORDER BY score DESC, text_score DESC, p.name ASC
LIMIT 20;
