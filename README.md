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

Check health:

```bash
docker compose ps
```

## 3) Apply migration

```bash
docker compose exec -T mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" < migrations/001_create_ai_rec_products.sql
```

Note: command uses variables from your shell. Run `source .env` first if needed.

## 4) Load products from YML

```bash
python3 scripts/load_yml_to_mysql.py --file data/products.yml
```

The loader reads MySQL connection settings from environment variables and also auto-loads `.env` from the project root.

## Reset database

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

## Useful commands

Stop DB:

```bash
docker compose down
```

Stop DB and remove data volume:

```bash
docker compose down -v
```
