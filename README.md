# Mysql AI Rec Prototype

This repo contains MySQL search prototypes for product ranking experiments.

Each prototype lives in its own folder and includes:
- `my.cnf`
- `migration.sql`
- `load.py` (prototype-specific loading logic)
- `query/search_products.sql`
- `query/search_products_with_param_score.sql`

Prototypes:
- `prototypes/p1` — отдельная таблица `product_attributes`, FULLTEXT по `name, description`
- `prototypes/p2` — атрибуты в поле `attributes` (TEXT), FULLTEXT по `name, description, attributes`

## 1) Configure environment

Copy env template:

```bash
cp .env.example .env
```

Edit `.env` if you want custom port, passwords, or database name.

## 2) Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 3) Load prototype by code

```bash
./scripts/load_prototype.sh p1
# or
./scripts/load_prototype.sh p2
```

What this script does:
- starts MySQL with prototype-specific `my.cnf`
- drops and recreates database from `.env`
- applies prototype migration
- loads `data/products.yml` via prototype `load.py`

## SQL searches

For prototype `p1`, run queries from:
- `prototypes/p1/query/search_products.sql`
- `prototypes/p1/query/search_products_with_param_score.sql`

Main query logic (p1):
- `text_score` from `MATCH(name, description) AGAINST(@q IN NATURAL LANGUAGE MODE)`
- `param_score` +1 per matched attribute pair (`name` exact + `value LIKE '%...%'`)
- ranking by `param_score DESC`, then `text_score DESC`

For prototype `p2`, run queries from:
- `prototypes/p2/query/search_products.sql`
- `prototypes/p2/query/search_products_with_param_score.sql`

Main query logic (p2):
- `text_score` from `MATCH(name, description, attributes) AGAINST(@q IN NATURAL LANGUAGE MODE)`
- атрибуты хранятся в поле `attributes` как `значение; значение; ...`
- `param_score` +1 per matched value via `attributes LIKE '%value%'`
- ranking by `param_score DESC`, then `text_score DESC`
