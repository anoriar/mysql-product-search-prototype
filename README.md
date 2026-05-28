# Mysql AI Rec Prototype

Small local MySQL project with:
- product catalog in `data/products.yml`
- schema migration in `migrations/001_create_ai_rec_products.sql`
- loader script `scripts/load_yml_to_mysql.py`
- SQL search examples in `sql/`

## 1) Configure environment

Copy env template:

```bash
cp .env.example .env
```

Edit `.env` if you want custom port, passwords, or database name.

## 2) Start database

```bash
docker compose up -d
```

## 3) Install Python dependencies

```bash
python3 -m pip install -r requirements.txt
```

## Reset database and load products

Full reset (drop DB, recreate, apply migration, reload `products.yml`):

```bash
./scripts/reset.sh
```

`reset.sh` also reads `.env`, so database name and credentials stay in one place.

## SQL searches

### Text search

See `sql/search_products.sql`.

This file contains examples of:
- fulltext `MATCH(name, description) AGAINST(...)`
- weighted score between name and description

### Text + parameters score

See `sql/search_products_with_param_score.sql`.

It computes:
- `text_score` using `MATCH ... AGAINST(@q IN NATURAL LANGUAGE MODE)`
- `param_score` as `+1` for each requested parameter where:
  - parameter name matches exactly
  - parameter value matches `LIKE '%value%'`
- final `score = text_score + param_score`
