import json
import re
from datetime import datetime, timezone as datetime_timezone

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from shop.models import Product, ProductImage


PRODUCT_COLUMNS = {
    "id",
    "name",
    "category",
    "fabric",
    "color",
    "occasion",
    "price",
    "mrp",
    "rating",
    "stock",
    "colors",
    "description",
    "image",
    "active",
    "created_at",
}
IMAGE_NAME = re.compile(r"[a-f0-9]{32}\.(?:jpg|png|webp)")


class Command(BaseCommand):
    help = "Import the previous app's product catalog and referenced image bytes."

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Django catalog already exists; skipping legacy import.")
            return

        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            if "products" not in tables:
                self.stdout.write("No legacy product table found.")
                return
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, "products")
            }
            missing = PRODUCT_COLUMNS - columns
            if missing:
                raise CommandError(
                    "The legacy products table is missing required columns: "
                    + ", ".join(sorted(missing))
                )
            cursor.execute(
                "SELECT id,name,category,fabric,color,occasion,price,mrp,rating,stock,"
                "colors,description,image,active,created_at FROM products "
                "ORDER BY created_at,id"
            )
            rows = [
                dict(zip((column[0] for column in cursor.description), row))
                for row in cursor.fetchall()
            ]
            image_names = {
                match.group(1)
                for row in rows
                if isinstance(row["image"], str)
                if (match := re.fullmatch(r"/uploads/([a-f0-9]{32}\.(?:jpg|png|webp))", row["image"]))
            }

            images = {}
            if "media" in tables and image_names:
                placeholders = ",".join(["%s"] * len(image_names))
                cursor.execute(
                    f"SELECT name,content_type,data FROM media WHERE name IN ({placeholders})",
                    list(image_names),
                )
                images = {
                    row[0]: ProductImage(name=row[0], content_type=row[1], data=row[2])
                    for row in cursor.fetchall()
                }

        products = []
        for row in rows:
            try:
                colors = json.loads(row["colors"])
                if not isinstance(colors, list):
                    raise ValueError
                created_at = datetime.fromtimestamp(
                    float(row["created_at"]),
                    tz=datetime_timezone.utc,
                )
            except (TypeError, ValueError, json.JSONDecodeError, OverflowError) as exc:
                raise CommandError(
                    f"Could not import legacy product {row['id']}: invalid colors or timestamp."
                ) from exc
            image_name = ""
            if row["image"] and row["image"].startswith("/uploads/"):
                candidate = row["image"].removeprefix("/uploads/")
                if candidate in images and IMAGE_NAME.fullmatch(candidate):
                    image_name = candidate
            products.append(
                Product(
                    name=row["name"],
                    category=row["category"],
                    fabric=row["fabric"],
                    color=row["color"],
                    occasion=row["occasion"],
                    price=row["price"],
                    mrp=row["mrp"],
                    rating=row["rating"],
                    stock=row["stock"],
                    colors=colors,
                    description=row["description"],
                    image_name=image_name,
                    active=bool(row["active"]),
                    created_at=created_at,
                )
            )

        with transaction.atomic():
            if Product.objects.exists():
                self.stdout.write("Django catalog was populated concurrently; skipping import.")
                return
            ProductImage.objects.bulk_create(list(images.values()))
            Product.objects.bulk_create(products)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(products)} legacy products and {len(images)} images."))
