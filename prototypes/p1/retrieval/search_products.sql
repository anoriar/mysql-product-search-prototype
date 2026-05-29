SET @q = 'Кеды Vans Sk8-Hi M191 Кроссовки с усиленным мысом и пяткой дольше сохраняют форму. Упругая подошва снижает ударную нагрузку на стопу.';
SELECT offer_id, name, description,
    (
        MATCH(name, description) AGAINST(@q IN NATURAL LANGUAGE MODE)
    ) AS score
FROM products
ORDER BY score DESC, name ASC
LIMIT 20;
