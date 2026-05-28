CREATE TABLE IF NOT EXISTS products (
    offer_id VARCHAR(64) NOT NULL,
    url VARCHAR(255) NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price INT NOT NULL,
    currencyId VARCHAR(16) NOT NULL,
    categoryId INT NOT NULL,
    picture VARCHAR(255) NOT NULL,
    PRIMARY KEY (offer_id),
    UNIQUE KEY uq_products_offer_id (offer_id),
    UNIQUE KEY uq_products_url (url),
    FULLTEXT KEY ft_products_name_description (name, description) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_attributes (
    offer_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    value VARCHAR(255) NOT NULL,
    PRIMARY KEY (offer_id, name, value),
    KEY idx_product_attributes_offer_id (offer_id),
    CONSTRAINT fk_product_attributes_offer_id
        FOREIGN KEY (offer_id) REFERENCES products (offer_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
