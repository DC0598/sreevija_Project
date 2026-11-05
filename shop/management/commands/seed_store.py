from django.core.management.base import BaseCommand

from shop.models import Product


PRODUCTS = [
    ("Royal Kanjivaram Silk", "Kanjivaram", "Pure Silk", "Rose", "Wedding", 12999, 15999, 4.8, 5, ["#e8a0b4", "#f3d9a4"], "Handwoven pure zari Kanjivaram with temple border and rich pallu."),
    ("Soft Silk Gold Zari", "Silk", "Silk Blend", "Gold", "Festive", 8999, 10999, 4.6, 8, ["#f3d9a4", "#e8cfa0"], "Lightweight soft silk with graceful gold zari motifs."),
    ("Kanjivaram Temple Border Mint", "Kanjivaram", "Pure Silk", "Mint", "Festive", 9499, 11499, 4.5, 7, ["#a8d5c2", "#f3d9a4"], "Pure Kanjivaram in mint with a contrast temple border."),
    ("Mysore Silk Emerald", "Silk", "Pure Silk", "Green", "Festive", 6499, 7999, 4.7, 12, ["#a8d5c2", "#f3d9a4"], "Lustrous Mysore crepe silk with contrast border."),
    ("Chanderi Pastel Pink", "Silk", "Silk Blend", "Pink", "Party", 3499, 4499, 4.4, 15, ["#f4c2d0", "#fdeef2"], "Light and sheer silk with delicate buttis."),
    ("Soft Silk Butter Yellow", "Silk", "Silk Blend", "Yellow", "Festive", 4299, 5299, 4.5, 20, ["#f6d98a", "#f0c97a"], "Soft silk with a woven border, ideal for festive days."),
    ("Bridal Kanjivaram Rose", "Bridal", "Pure Silk", "Pink", "Wedding", 15999, 19999, 4.9, 3, ["#f2a7a7", "#f5dd9e"], "Statement bridal Kanjivaram with heavy zari work."),
    ("Kanjivaram Lavender Checks", "Kanjivaram", "Pure Silk", "Lavender", "Festive", 10999, 12999, 4.6, 6, ["#c9b6e4", "#f3d9a4"], "Soft lavender Kanjivaram with gold checks."),
    ("Bridal Peach Zari Silk", "Bridal", "Pure Silk", "Peach", "Wedding", 18999, 22999, 4.8, 4, ["#f6c9b3", "#f3d9a4"], "Rich bridal silk with full zari body and wide border."),
    ("Bridal Ivory Silk", "Bridal", "Pure Silk", "White", "Wedding", 7499, 8999, 4.5, 9, ["#f7efe0", "#e6d2a8"], "Ivory bridal silk with understated gold border."),
    ("Dharmavaram Pattu Peach Zari", "Dharmavaram", "Pure Silk", "Peach", "Wedding", 11499, 13999, 4.7, 6, ["#f6c9b3", "#f3d9a4"], "Traditional Dharmavaram pattu with a broad zari border and rich pallu."),
    ("Dharmavaram Pastel Green Pattu", "Dharmavaram", "Pure Silk", "Green", "Festive", 9999, 11999, 4.6, 8, ["#b9d3b4", "#f3d9a4"], "Handwoven Dharmavaram silk in soft green with contrast border."),
    ("Dharmavaram Rose Temple Border", "Dharmavaram", "Pure Silk", "Rose", "Festive", 10499, 12499, 4.5, 5, ["#f4c2d0", "#e8cfa0"], "Rose Dharmavaram with a temple-motif border."),
]


class Command(BaseCommand):
    help = "Create the starter product collection when the catalog is empty."

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Product catalog already exists; leaving it unchanged.")
            return
        Product.objects.bulk_create(
            [
                Product(
                    name=name,
                    category=category,
                    fabric=fabric,
                    color=color,
                    occasion=occasion,
                    price=price,
                    mrp=mrp,
                    rating=rating,
                    stock=stock,
                    colors=colors,
                    description=description,
                )
                for (
                    name, category, fabric, color, occasion, price, mrp,
                    rating, stock, colors, description,
                ) in PRODUCTS
            ]
        )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(PRODUCTS)} products."))
