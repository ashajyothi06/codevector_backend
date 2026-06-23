from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from app.cursor import InvalidCursorError, decode_cursor, encode_cursor
from app.database import get_connection
from app.schemas import ProductCreate, ProductOut, ProductPage, ProductUpdate


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_products_created_id
ON products (created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_products_category_created_id
ON products (category, created_at DESC, id DESC);
"""


def initialize_database() -> None:
    """Create the table and indexes when the API starts."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
            cursor.execute(CREATE_INDEXES_SQL)
        connection.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="CodeVector Product Browser API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "message": "CodeVector Product Browser API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


@app.get("/products", response_model=ProductPage)
def list_products(
    category: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
):
    """Return products newest first using keyset/cursor pagination."""
    cursor_data = None

    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
        except InvalidCursorError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if cursor_data["category"] != category:
            raise HTTPException(
                status_code=400,
                detail="Use the same category that was used for the first page",
            )

    conditions: list[str] = []
    params: dict[str, object] = {"fetch_limit": limit + 1}

    if category:
        conditions.append("category = %(category)s")
        params["category"] = category

    if cursor_data:
        conditions.append("created_at <= %(snapshot_at)s")
        conditions.append(
            "(created_at, id) < (%(last_created_at)s, %(last_id)s)"
        )
        params.update(cursor_data)
    else:
        # Database time is used so all servers use one consistent clock.
        with get_connection() as connection:
            with connection.cursor() as db_cursor:
                db_cursor.execute("SELECT CURRENT_TIMESTAMP")
                snapshot_at = db_cursor.fetchone()[0]
        conditions.append("created_at <= %(snapshot_at)s")
        params["snapshot_at"] = snapshot_at

    where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT id, name, category, price, created_at, updated_at
        FROM products
        {where_sql}
        ORDER BY created_at DESC, id DESC
        LIMIT %(fetch_limit)s
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as db_cursor:
            db_cursor.execute(sql, params)
            rows = db_cursor.fetchall()

    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    next_cursor = None

    if has_more and visible_rows:
        last_product = visible_rows[-1]
        next_cursor = encode_cursor(
            snapshot_at=params["snapshot_at"],
            last_created_at=last_product["created_at"],
            last_id=last_product["id"],
            category=category,
        )

    return {
        "items": visible_rows,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(product: ProductCreate):
    """Create a product. PostgreSQL generates id and timestamps."""
    sql = """
        INSERT INTO products (name, category, price)
        VALUES (%s, %s, %s)
        RETURNING id, name, category, price, created_at, updated_at
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, (product.name, product.category, product.price))
            row = cursor.fetchone()
        connection.commit()

    return row


@app.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, product: ProductUpdate):
    """
    Update name and/or price only.

    Category and created_at are intentionally not editable because changing them
    would move a product inside the paginated result while a user is browsing.
    """
    updates: list[str] = []
    values: list[str | Decimal | datetime | int] = []

    if product.name is not None:
        updates.append("name = %s")
        values.append(product.name)

    if product.price is not None:
        updates.append("price = %s")
        values.append(product.price)

    if not updates:
        raise HTTPException(status_code=400, detail="Provide name or price")

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(product_id)

    sql = f"""
        UPDATE products
        SET {", ".join(updates)}
        WHERE id = %s
        RETURNING id, name, category, price, created_at, updated_at
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, values)
            row = cursor.fetchone()
        connection.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return row
