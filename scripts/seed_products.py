import argparse

from app.database import get_connection


SEED_SQL = """
WITH generated AS (
    SELECT
        number,
        CURRENT_TIMESTAMP - random() * INTERVAL '365 days' AS created_time
    FROM generate_series(1, %(count)s) AS number
)
INSERT INTO products (name, category, price, created_at, updated_at)
SELECT
    'Product ' || number,
    (ARRAY['electronics', 'fashion', 'books', 'home', 'sports'])[
        1 + floor(random() * 5)::int
    ],
    round((10 + random() * 9990)::numeric, 2),
    created_time,
    created_time + random() * (CURRENT_TIMESTAMP - created_time)
FROM generated;
"""


def seed_products(count: int, clear_existing: bool) -> None:
    if count <= 0:
        raise ValueError("count must be greater than zero")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            if clear_existing:
                cursor.execute("TRUNCATE TABLE products RESTART IDENTITY")

            cursor.execute(SEED_SQL, {"count": count})
        connection.commit()

    print(f"Inserted {count:,} products successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate product test data")
    parser.add_argument("--count", type=int, default=200_000)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing products before inserting new products",
    )
    args = parser.parse_args()

    seed_products(args.count, args.clear)
