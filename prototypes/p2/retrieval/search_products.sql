SET @q = 'Кеды Vans Sk8-Hi M191 весна-осень; белый.';
SELECT offer_id, name, description, attributes,
    (
        MATCH(name, description, attributes) AGAINST(@q IN NATURAL LANGUAGE MODE)
    ) AS score
FROM products
ORDER BY score DESC, name ASC
LIMIT 20;
