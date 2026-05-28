#!/usr/bin/env python3
import argparse
import os
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import mysql.connector


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def to_int_price(raw_price: str) -> int:
    return int(Decimal(raw_price).quantize(Decimal("1")))


def parse_products(
    yml_path: str,
) -> tuple[
    list[tuple[str, str, str, str, int, str, int, str]],
    list[tuple[str, str, str]],
]:
    tree = ET.parse(yml_path)
    root = tree.getroot()
    products = []
    attributes = []

    for offer in root.findall(".//offer"):
        offer_id = (offer.get("id") or "").strip()
        url = (offer.findtext("url") or "").strip()
        name = (offer.findtext("name") or "").strip()
        description = (offer.findtext("description") or "").strip()
        price_raw = (offer.findtext("price") or "0").strip()
        currency_id = (offer.findtext("currencyId") or "").strip()
        category_id_raw = (offer.findtext("categoryId") or "0").strip()
        picture = (offer.findtext("picture") or "").strip()

        if not all([offer_id, url, name, description, currency_id, picture]):
            continue

        products.append(
            (
                offer_id,
                url,
                name,
                description,
                to_int_price(price_raw),
                currency_id,
                int(category_id_raw),
                picture,
            )
        )

        for param in offer.findall("param"):
            param_name = (param.get("name") or "").strip()
            param_value = (param.text or "").strip()
            param_unit = (param.get("unit") or "").strip()

            if not param_name or not param_value:
                continue

            if param_unit:
                param_value = f"{param_value} ({param_unit})"

            attributes.append((offer_id, param_name[:255], param_value[:255]))

    return products, attributes


def load_products(yml_path: str, db_config: dict) -> None:
    products, attributes = parse_products(yml_path)
    if not products:
        print("No valid products found in YML file.")
        return

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    query = """
    INSERT INTO products (
        offer_id, url, name, description, price, currencyId, categoryId, picture
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        url = VALUES(url),
        name = VALUES(name),
        description = VALUES(description),
        price = VALUES(price),
        currencyId = VALUES(currencyId),
        categoryId = VALUES(categoryId),
        picture = VALUES(picture)
    """

    insert_attributes_query = """
    INSERT INTO product_attributes (offer_id, name, value)
    VALUES (%s, %s, %s)
    """

    offer_ids = sorted({product[0] for product in products})
    placeholders = ", ".join(["%s"] * len(offer_ids))
    delete_attributes_query = (
        f"DELETE FROM product_attributes WHERE offer_id IN ({placeholders})"
    )

    cursor.executemany(query, products)
    if offer_ids:
        cursor.execute(delete_attributes_query, offer_ids)
    if attributes:
        cursor.executemany(insert_attributes_query, attributes)
    conn.commit()

    print(
        f"Loaded {len(products)} products into products "
        f"and {len(attributes)} rows into product_attributes."
    )

    cursor.close()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load YML products into MySQL.")
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")
    parser.add_argument(
        "--file",
        default=str(project_root / "data" / "products.yml"),
        help="Path to products YML file (default: data/products.yml)",
    )
    args = parser.parse_args()

    db_config = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "ai_user"),
        "password": os.getenv("MYSQL_PASSWORD", "ai_pass"),
        "database": os.getenv("MYSQL_DATABASE", "ai_rec_db"),
        "charset": "utf8mb4",
    }

    load_products(args.file, db_config)


if __name__ == "__main__":
    main()
