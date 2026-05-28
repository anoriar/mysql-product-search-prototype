# Mysql AI Rec Prototype

This repo contains MySQL search prototypes for product ranking experiments.

Each prototype lives in its own folder and includes:
- `my.cnf`
- `migration.sql`
- `load.py` (prototype-specific loading logic)
- `query/search_products.sql`
- `query/search_products_with_param_score.sql`

Current prototype:
- `prototypes/p1_current`

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
./scripts/load_prototype.sh p1_current
```

What this script does:
- starts MySQL with prototype-specific `my.cnf`
- drops and recreates database from `.env`
- applies prototype migration
- loads `data/products.yml` via prototype `load.py`

## SQL searches

For prototype `p1_current`, run queries from:
- `prototypes/p1_current/query/search_products.sql`
- `prototypes/p1_current/query/search_products_with_param_score.sql`

Main query logic:
- `text_score` from `MATCH(name, description) AGAINST(@q IN NATURAL LANGUAGE MODE)`
- `param_score` +1 per matched attribute pair (`name` exact + `value LIKE '%...%'`)
- ranking by `param_score DESC`, then `text_score DESC`
