# SET @q = 'офе';

# SELECT offer_id, name, description,
#        MATCH(name, description) AGAINST(CONCAT('+', @q, '*') IN BOOLEAN MODE) AS relevance
# FROM products
# WHERE MATCH(name, description) AGAINST(CONCAT('+', @q, '*') IN BOOLEAN MODE)
# ORDER BY relevance DESC, name ASC
# LIMIT 20;


SET @name = 'Кеды Puma Smash M151';
SET @description = 'Пара лоферов на удобной основе уменьшает нагрузку на стопу при длительной ходьбе. Мягкая внутренняя отделка предотвращает натирание.'
SELECT offer_id, name, description,
    (
        3 * MATCH(name, description) AGAINST(@name IN NATURAL LANGUAGE MODE)
        +
        1 * MATCH(name, description) AGAINST(@description IN NATURAL LANGUAGE MODE)
    ) AS score
FROM products
ORDER BY score DESC, name ASC
LIMIT 20;