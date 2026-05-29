#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any

import mysql.connector
from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """\
Ты — AI recommendation manager. Твоя задача — подобрать похожие товары на основе исходного товара.

Алгоритм:
1. Разбери name и description: найди характеристики товара — бренд, модельную линейку, \
параметры, назначение, цвет, пол и другие слова, связанные с характеристиками.
2. Объедини найденное с attributes (список значений), убери дубликаты.
3. Отсортируй характеристики по приоритету и назначь каждой вес от 1 до 9 \
(9 — самый высокий приоритет). Пример приоритетов: пол → бренд → модель → цвет → \
материал → сезон → назначение → прочие параметры.
4. Оставь не более 7–9 наиболее значимых параметров.

5. Вызови ровно один tool:
   - если параметров не найдено — defaultQuery(name, description, attributes);
   - если параметры найдены — queryWithParams с массивом {value, weight}.

6. Получив результат tool, верни JSON-массив рекомендаций. Каждый элемент:
   {"id": "...", "name": "...", "description": "...", "score": <число>}
   Используй id из поля offer_id результата tool. score — релевантность из MATCH.
   Верни только JSON, без пояснений."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "defaultQuery",
            "description": (
                "Поиск похожих товаров по полному тексту name, description и attributes, "
                "когда не удалось выделить отдельные параметры."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "attributes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "description", "attributes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "queryWithParams",
            "description": (
                "Поиск похожих товаров с взвешенным FULLTEXT по выделенным параметрам."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "params": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "weight": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 9,
                                },
                            },
                            "required": ["value", "weight"],
                        },
                    },
                },
                "required": ["params"],
            },
        },
    },
]


def get_project_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".env").is_file():
            return parent
    return path.parents[3]


def load_env() -> None:
    load_dotenv(dotenv_path=get_project_root() / ".env")


def get_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


def get_db_config() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": get_env_int("MYSQL_PORT", 3306),
        "user": os.getenv("MYSQL_USER", "ai_user"),
        "password": os.getenv("MYSQL_PASSWORD", "ai_pass"),
        "database": os.getenv("MYSQL_DATABASE", "ai_rec_db"),
        "charset": "utf8mb4",
    }


def parse_attributes(attributes: str) -> list[str]:
    return [part.strip() for part in attributes.split(";") if part.strip()]


def fetch_product_by_id(cursor: mysql.connector.cursor.MySQLCursor, offer_id: str) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT offer_id, name, description, attributes
        FROM products
        WHERE offer_id = %s
        """,
        (offer_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Product not found: {offer_id}")

    return {
        "offer_id": row[0],
        "name": row[1],
        "description": row[2],
        "attributes": row[3],
        "attributes_list": parse_attributes(row[3]),
    }


def rows_to_products(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [
        {
            "offer_id": row[0],
            "name": row[1],
            "description": row[2],
            "score": float(row[3]) if row[3] is not None else 0.0,
        }
        for row in rows
    ]


def default_query(
    cursor: mysql.connector.cursor.MySQLCursor,
    name: str,
    description: str,
    attributes: list[str],
    exclude_offer_id: str | None = None,
) -> list[dict[str, Any]]:
    query_text = "; ".join(part for part in [name, description, *attributes] if part.strip())
    where_clause = ""
    params: list[Any] = [query_text]
    if exclude_offer_id:
        where_clause = "WHERE offer_id != %s"
        params.append(exclude_offer_id)

    sql = f"""
        SELECT offer_id, name, description, score
        FROM (
            SELECT offer_id, name, description,
                MATCH(name, description, attributes) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score
            FROM products
            {where_clause}
        ) ranked
        WHERE score > 0
        ORDER BY score DESC, name ASC
        LIMIT 20
    """
    cursor.execute(sql, params)
    return rows_to_products(cursor.fetchall())


def query_with_params(
    cursor: mysql.connector.cursor.MySQLCursor,
    params: list[dict[str, Any]],
    exclude_offer_id: str | None = None,
) -> list[dict[str, Any]]:
    if not params:
        return []

    score_parts = []
    query_params: list[Any] = []
    for param in params:
        score_parts.append(
            "%s * MATCH(name, description, attributes) AGAINST(%s IN NATURAL LANGUAGE MODE)"
        )
        query_params.extend([param["weight"], param["value"]])

    score_expr = " + ".join(score_parts)
    where_clause = ""
    if exclude_offer_id:
        where_clause = "WHERE offer_id != %s"
        query_params.append(exclude_offer_id)

    sql = f"""
        SELECT offer_id, name, description, score
        FROM (
            SELECT offer_id, name, description, ({score_expr}) AS score
            FROM products
            {where_clause}
        ) ranked
        WHERE score > 0
        ORDER BY score DESC, name ASC
        LIMIT 20
    """
    cursor.execute(sql, query_params)
    return rows_to_products(cursor.fetchall())


def execute_tool(
    cursor: mysql.connector.cursor.MySQLCursor,
    tool_name: str,
    arguments: dict[str, Any],
    exclude_offer_id: str,
) -> list[dict[str, Any]]:
    if tool_name == "defaultQuery":
        return default_query(
            cursor,
            name=arguments["name"],
            description=arguments["description"],
            attributes=arguments["attributes"],
            exclude_offer_id=exclude_offer_id,
        )

    if tool_name == "queryWithParams":
        return query_with_params(
            cursor,
            params=arguments["params"],
            exclude_offer_id=exclude_offer_id,
        )

    raise ValueError(f"Unknown tool: {tool_name}")


def extract_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("LLM response must be a JSON array.")
    return parsed


def normalize_recommendations(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for product in products:
        normalized.append(
            {
                "id": product.get("id") or product.get("offer_id"),
                "name": product.get("name", ""),
                "description": product.get("description", ""),
                "score": float(product.get("score", 0)),
            }
        )
    return normalized


def normalize_parameters(params: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "value": param["value"],
            "weight": int(param["weight"]),
        }
        for param in params
    ]


def normalize_source_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": product["offer_id"],
        "name": product["name"],
        "description": product["description"],
        "attributes": product["attributes_list"],
    }


def build_tool_query(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "queryWithParams":
        return {
            "type": tool_name,
            "params": normalize_parameters(arguments["params"]),
        }

    return {
        "type": tool_name,
        "name": arguments["name"],
        "description": arguments["description"],
        "attributes": arguments["attributes"],
    }


def build_result(
    source_product: dict[str, Any],
    tool_query: dict[str, Any],
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_product": normalize_source_product(source_product),
        "tool_query": tool_query,
        "products": normalize_recommendations(products),
    }


def recommend_similar_products(
    offer_id: str, db_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY is not set. Add it to .env in the project root."
        )

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    conn = mysql.connector.connect(**(db_config or get_db_config()))
    cursor = conn.cursor()

    try:
        product = fetch_product_by_id(cursor, offer_id)
        user_message = (
            "Исходный товар:\n"
            f"name: {product['name']}\n"
            f"description: {product['description']}\n"
            f"attributes: {json.dumps(product['attributes_list'], ensure_ascii=False)}"
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        tool_query: dict[str, Any] = {}

        for _ in range(5):
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            message = response.choices[0].message

            if message.tool_calls:
                messages.append(message.model_dump(exclude_none=True))

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    tool_query = build_tool_query(tool_name, arguments)
                    tool_result = execute_tool(
                        cursor,
                        tool_name,
                        arguments,
                        exclude_offer_id=product["offer_id"],
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )
                continue

            if message.content:
                products = extract_json_array(message.content)
                return build_result(product, tool_query, products)

            raise ValueError("LLM returned empty response.")

        raise ValueError("LLM tool-calling loop exceeded maximum iterations.")
    finally:
        cursor.close()
        conn.close()


def print_recommendations(result: dict[str, Any]) -> None:
    print("=== Source product ===")
    print(json.dumps(result["source_product"], ensure_ascii=False, indent=2))
    print()
    print("=== Tool query ===")
    print(json.dumps(result["tool_query"], ensure_ascii=False, indent=2))
    print()
    print("=== Products ===")
    print(json.dumps(result["products"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recommend similar products for p2 prototype using DeepSeek."
    )
    load_env()
    parser.add_argument(
        "--id",
        required=True,
        help="Source product offer_id",
    )
    args = parser.parse_args()

    result = recommend_similar_products(args.id, get_db_config())
    print_recommendations(result)


if __name__ == "__main__":
    main()
