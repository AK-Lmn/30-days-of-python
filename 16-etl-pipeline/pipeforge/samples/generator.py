import csv
import json
import random
from pathlib import Path


class SampleDataGenerator:
    FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Evan", "Fiona", "George", "Hannah", "Ian", "Julia"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson"]
    PRODUCTS = ["Wireless Headphones", "Mechanical Keyboard", "Ultra-Wide Monitor", "Ergonomic Chair", "USB-C Dock", "Webcam HD"]
    CATEGORIES = ["Electronics", "Electronics", "Hardware", "Furniture", "Accessories", "Electronics"]
    CITIES = ["New York", "San Francisco", "Austin", "Seattle", "Chicago", "Boston", "Denver"]
    STATUSES = ["completed", "pending", "processing", "refunded"]

    @classmethod
    def generate_orders_csv(cls, target_path: Path | str, count: int = 100, include_dirty_rows: bool = True) -> Path:
        out_path = Path(target_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = ["order_id", "customer_name", "customer_email", "product", "category", "price", "quantity", "order_date", "status", "city"]
        
        with open(out_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i in range(1, count + 1):
                first = random.choice(cls.FIRST_NAMES)
                last = random.choice(cls.LAST_NAMES)
                email = f"{first.lower()}.{last.lower()}@example.com"
                prod_idx = random.randint(0, len(cls.PRODUCTS) - 1)
                product = cls.PRODUCTS[prod_idx]
                category = cls.CATEGORIES[prod_idx]
                price = round(random.uniform(25.0, 850.0), 2)
                quantity = random.randint(1, 5)
                day = random.randint(1, 28)
                month = random.randint(1, 12)
                order_date = f"2026-{month:02d}-{day:02d}"
                status = random.choice(cls.STATUSES)
                city = random.choice(cls.CITIES)

                if include_dirty_rows and i % 15 == 0:
                    email = "invalid-email-address"
                elif include_dirty_rows and i % 25 == 0:
                    price = -99.99
                elif include_dirty_rows and i % 35 == 0:
                    first = "   "
                    last = "   "

                writer.writerow({
                    "order_id": f"ORD-{1000 + i}",
                    "customer_name": f"{first} {last}",
                    "customer_email": email,
                    "product": product,
                    "category": category,
                    "price": str(price),
                    "quantity": str(quantity),
                    "order_date": order_date,
                    "status": status,
                    "city": city,
                })

        return out_path

    @classmethod
    def generate_users_json(cls, target_path: Path | str, count: int = 50, lines: bool = False) -> Path:
        out_path = Path(target_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        users = []
        for i in range(1, count + 1):
            first = random.choice(cls.FIRST_NAMES)
            last = random.choice(cls.LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}@corp.io"
            user = {
                "user_id": 2000 + i,
                "first_name": first,
                "last_name": last,
                "email": email,
                "age": random.randint(18, 70),
                "signup_date": f"2026-0{random.randint(1, 9)}-{random.randint(10, 25)}",
                "active": random.choice([True, False]),
            }
            users.append(user)

        with open(out_path, mode="w", encoding="utf-8") as f:
            if lines:
                for u in users:
                    f.write(json.dumps(u) + "\n")
            else:
                json.dump(users, f, indent=2)

        return out_path
