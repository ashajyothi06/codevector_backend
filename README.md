# CodeVector Product Browser

A small FastAPI + PostgreSQL backend for browsing approximately 200,000 products newest first, filtering by category, and paginating without slow `OFFSET` queries.

## Why this approach?

The API uses cursor/keyset pagination with this stable order:

```sql
ORDER BY created_at DESC, id DESC
```

`id` breaks ties when products have the same `created_at` value. The cursor also stores a snapshot timestamp, so products inserted after page 1 do not appear in the middle of the same browsing session.

To keep pagination stable, `id`, `created_at`, and `category` are treated as immutable. The update endpoint only allows changing `name` and `price`.

## Project structure

```text
app/main.py              API endpoints and SQL queries
app/database.py          PostgreSQL connection helper
app/config.py            Reads DATABASE_URL
app/cursor.py            Cursor encode/decode functions
app/schemas.py           Request and response models
scripts/seed_products.py Fast bulk data generation
scripts/check_pagination.py Checks for duplicate IDs across pages
tests/test_cursor.py     Cursor unit tests
```

## 1. Create a PostgreSQL database

Example database name:

```text
codevector_products
```

## 2. Set up the project

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and update the connection string:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/codevector_products
```

## 3. Start the API once

```bash
uvicorn app.main:app --reload
```

The startup code creates the `products` table and indexes automatically.

Open:

```text
http://127.0.0.1:8000/docs
```

## 4. Insert 200,000 products

Open another terminal with the virtual environment active:

```bash
python -m scripts.seed_products --count 200000 --clear
```

This uses PostgreSQL `generate_series`, so all products are generated in one bulk SQL statement instead of 200,000 slow individual inserts.

## API examples

First page:

```http
GET /products?limit=20
```

Filter by category:

```http
GET /products?category=books&limit=20
```

Next page:

```http
GET /products?category=books&limit=20&cursor=PASTE_NEXT_CURSOR_HERE
```

Create a product:

```http
POST /products
Content-Type: application/json

{
  "name": "New Laptop",
  "category": "electronics",
  "price": 59999.00
}
```

Update a product without moving it in pagination:

```http
PATCH /products/1
Content-Type: application/json

{
  "name": "Updated Product Name",
  "price": 499.00
}
```

## Check pagination

With the API running:

```bash
python -m scripts.check_pagination --url http://127.0.0.1:8000 --limit 100
```

For one category:

```bash
python -m scripts.check_pagination --url http://127.0.0.1:8000 --category books --limit 100
```

## Run unit tests

```bash
pytest
```

## Important correctness assumption

The columns used to decide result membership and order are not editable:

- `id`
- `created_at`
- `category`

Updates can change `name`, `price`, and `updated_at`. New products created after the first page are excluded from that browsing session by the snapshot timestamp.

## Deployment

1. Create a free PostgreSQL database on Neon or Supabase.
2. Run the API once so the table and indexes are created.
3. Run the seed script using the hosted `DATABASE_URL`.
4. Create a Render web service from the GitHub repository.
5. Add `DATABASE_URL` as an environment variable.
6. Use this start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## What I would improve with more time

- Sign cursors so clients cannot edit them.
- Add integration tests with a temporary PostgreSQL database.
- Add structured logging and monitoring.
- Add a small frontend.
- Add version history if category changes must be supported during an active browsing session.
