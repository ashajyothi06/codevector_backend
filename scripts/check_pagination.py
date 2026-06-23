import argparse

import requests


def check_pagination(base_url: str, category: str | None, limit: int) -> None:
    seen_ids: set[int] = set()
    cursor = None
    page_number = 1

    while True:
        params = {"limit": limit}
        if category:
            params["category"] = category
        if cursor:
            params["cursor"] = cursor

        response = requests.get(f"{base_url.rstrip('/')}/products", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        ids = [item["id"] for item in data["items"]]
        duplicates = seen_ids.intersection(ids)
        if duplicates:
            raise RuntimeError(f"Duplicate product ids found: {sorted(duplicates)}")

        seen_ids.update(ids)
        print(f"Page {page_number}: {len(ids)} products, total checked: {len(seen_ids)}")

        cursor = data["next_cursor"]
        if not cursor:
            break
        page_number += 1

    print(f"Pagination check passed. {len(seen_ids):,} unique products were read.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check that pages contain no duplicates")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--category", default=None)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    check_pagination(args.url, args.category, args.limit)
