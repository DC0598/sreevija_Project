import json
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .models import (
    NewsletterSubscriber,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Wishlist,
)

User = get_user_model()


class AdditionalAdminCommandTests(TestCase):
    def test_creates_admin_once_without_resetting_existing_password(self):
        variables = {
            "ADDITIONAL_ADMIN_USERNAME": "admin",
            "ADDITIONAL_ADMIN_PASSWORD": "HighEntropy!Passphrase742",
        }
        with patch.dict("os.environ", variables):
            call_command("create_additional_admin")
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.check_password(variables["ADDITIONAL_ADMIN_PASSWORD"]))

        variables["ADDITIONAL_ADMIN_PASSWORD"] = "Changed!Passphrase9876"
        with patch.dict("os.environ", variables):
            call_command("create_additional_admin")
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("HighEntropy!Passphrase742"))

    def test_rejects_short_additional_admin_password(self):
        with patch.dict(
            "os.environ",
            {
                "ADDITIONAL_ADMIN_USERNAME": "admin",
                "ADDITIONAL_ADMIN_PASSWORD": "short",
            },
        ):
            with self.assertRaises(CommandError):
                call_command("create_additional_admin")
        self.assertFalse(User.objects.filter(username="admin").exists())


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Rose Silk Saree",
            category="Silk",
            fabric="Pure Silk",
            color="Rose",
            occasion="Festive",
            price=1800,
            mrp=2200,
            rating=4.8,
            stock=5,
            colors=["#e8a0b4", "#f3d9a4"],
            description="A test saree",
        )

    def test_home_catalog_and_product_detail_render(self):
        self.assertContains(self.client.get(reverse("home")), "Bestsellers")
        listing = self.client.get(reverse("shop"), {"category": "Silk", "sort": "low"})
        self.assertContains(listing, self.product.name)
        self.assertContains(self.client.get(reverse("product", args=[self.product.pk])), self.product.description)

    def test_registration_login_wishlist_and_logout(self):
        response = self.client.post(
            reverse("register"),
            {"name": "Test Buyer", "email": "buyer@example.com", "password": "Long!Passphrase742"},
        )
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(email="buyer@example.com")
        self.assertTrue(user.check_password("Long!Passphrase742"))

        self.client.post(reverse("wishlist_toggle", args=[self.product.pk]), {"return_to": reverse("product", args=[self.product.pk])})
        self.assertTrue(Wishlist.objects.filter(user=user, product=self.product).exists())
        self.assertContains(self.client.get(reverse("wishlist")), self.product.name)

        self.client.post(reverse("logout"))
        login = self.client.post(
            reverse("login"),
            {"identifier": "buyer@example.com", "password": "Long!Passphrase742"},
        )
        self.assertRedirects(login, reverse("home"))

    def test_staff_can_log_in_with_username(self):
        User.objects.create_superuser(
            username="admin",
            email="",
            password="Secure!AdminPassphrase742",
        )
        response = self.client.post(
            reverse("login"),
            {"identifier": "admin", "password": "Secure!AdminPassphrase742"},
        )
        self.assertRedirects(response, reverse("manage"))
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_checkout_uses_database_price_and_decrements_stock(self):
        self.client.post(reverse("cart_add", args=[self.product.pk]), {"qty": "2"})
        response = self.client.post(
            reverse("checkout"),
            {
                "name": "Guest Buyer",
                "phone": "9876543210",
                "email": "guest@example.com",
                "address": "12 Test Street",
                "city": "Chennai",
                "pincode": "600001",
                "payment_method": "Cash on Delivery",
            },
        )
        order = Order.objects.get()
        self.assertRedirects(response, reverse("order_confirmation", args=[order.pk]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual((order.subtotal, order.shipping, order.total), (3600, 0, 3600))
        self.assertEqual(order.items.get().qty, 2)

    def test_order_cancellation_restocks_only_once(self):
        staff = User.objects.create_superuser(
            username="staff@example.com",
            email="staff@example.com",
            password="Staff!Passphrase742",
        )
        order = Order.objects.create(
            name="Guest Buyer",
            phone="9876543210",
            email="guest@example.com",
            address="12 Test Street",
            city="Chennai",
            pincode="600001",
            payment_method="Cash on Delivery",
            subtotal=1800,
            shipping=99,
            total=1899,
        )
        OrderItem.objects.create(order=order, product=self.product, name=self.product.name, price=1800, qty=2)
        self.product.stock = 0
        self.product.save(update_fields=["stock"])
        self.client.force_login(staff)

        self.client.post(
            reverse("manage_order", args=[order.pk]),
            {"status": "Cancelled", "payment_status": "Pending"},
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.client.post(
            reverse("manage_order", args=[order.pk]),
            {"status": "Placed", "payment_status": "Pending"},
        )
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(order.status, "Cancelled")

    def test_staff_upload_is_stored_in_database_and_served(self):
        staff = User.objects.create_superuser(
            username="staff@example.com",
            email="staff@example.com",
            password="Staff!Passphrase742",
        )
        self.client.force_login(staff)
        image_bytes = b"\x89PNG\r\n\x1a\nsample-image"
        response = self.client.post(
            reverse("manage_product_add"),
            {
                "name": "Uploaded Saree",
                "category": "Silk",
                "fabric": "Pure Silk",
                "color": "Pink",
                "occasion": "Festive",
                "price": 2000,
                "mrp": 2400,
                "rating": 4.5,
                "stock": 2,
                "description": "Image upload test",
                "c1": "#e8a0b4",
                "c2": "#f3d9a4",
                "image_upload": SimpleUploadedFile("test.png", image_bytes, content_type="image/png"),
            },
        )
        self.assertRedirects(response, reverse("manage"))
        product = Product.objects.get(name="Uploaded Saree")
        image = ProductImage.objects.get(pk=product.image_name)
        self.assertEqual(bytes(image.data), image_bytes)
        served = self.client.get(reverse("product_image", args=[image.name]))
        self.assertEqual(served.content, image_bytes)
        self.assertEqual(served["Content-Type"], "image/png")

    def test_invalid_product_image_is_rejected(self):
        staff = User.objects.create_superuser(
            username="staff@example.com",
            email="staff@example.com",
            password="Staff!Passphrase742",
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("manage_product_add"),
            {
                "name": "Bad Image Saree",
                "category": "Silk",
                "fabric": "Pure Silk",
                "color": "Pink",
                "occasion": "Festive",
                "price": 2000,
                "mrp": 2400,
                "rating": 4.5,
                "stock": 2,
                "description": "Image validation test",
                "c1": "#e8a0b4",
                "c2": "#f3d9a4",
                "image_upload": SimpleUploadedFile("bad.txt", b"not an image", content_type="image/png"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Bad Image Saree").exists())

    def test_staff_dashboard_renders_and_newsletter_subscribes(self):
        staff = User.objects.create_superuser(
            username="staff@example.com",
            email="staff@example.com",
            password="Staff!Passphrase742",
        )
        self.client.force_login(staff)
        order = Order.objects.create(
            name="Guest Buyer",
            phone="9876543210",
            email="guest@example.com",
            address="12 Test Street",
            city="Chennai",
            pincode="600001",
            payment_method="Cash on Delivery",
            subtotal=1800,
            shipping=99,
            total=1899,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            name=self.product.name,
            price=self.product.price,
            qty=1,
        )
        dashboard = self.client.get(reverse("manage"))
        self.assertContains(dashboard, "Admin Dashboard")
        self.assertContains(dashboard, self.product.name)
        self.assertContains(dashboard, '<table class="admin-order-table">')
        self.assertContains(dashboard, "guest@example.com")
        self.assertContains(dashboard, order.pk)
        response = self.client.post(reverse("newsletter"), {"email": "reader@example.com"})
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(NewsletterSubscriber.objects.filter(email="reader@example.com").exists())


class LegacyImportTests(TestCase):
    def test_imports_existing_catalog_and_referenced_image(self):
        image_bytes = b"\x89PNG\r\n\x1a\nlegacy-image"
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE products ("
                "id INTEGER PRIMARY KEY,name TEXT,category TEXT,fabric TEXT,color TEXT,"
                "occasion TEXT,price INTEGER,mrp INTEGER,rating REAL,stock INTEGER,"
                "colors TEXT,description TEXT,image TEXT,active INTEGER,created_at REAL)"
            )
            cursor.execute(
                "CREATE TABLE media (name TEXT PRIMARY KEY,content_type TEXT,data BLOB)"
            )
            cursor.execute(
                "INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    1,
                    "Legacy Saree",
                    "Silk",
                    "Pure Silk",
                    "Rose",
                    "Festive",
                    3000,
                    3500,
                    4.7,
                    4,
                    json.dumps(["#e8a0b4", "#f3d9a4"]),
                    "Imported product",
                    "/uploads/0123456789abcdef0123456789abcdef.png",
                    1,
                    time.time(),
                ],
            )
            cursor.execute(
                "INSERT INTO media VALUES (?,?,?)",
                [
                    "0123456789abcdef0123456789abcdef.png",
                    "image/png",
                    image_bytes,
                ],
            )

        call_command("import_legacy_products", verbosity=0)
        call_command("seed_store", verbosity=0)
        product = Product.objects.get(name="Legacy Saree")
        image = ProductImage.objects.get(pk=product.image_name)
        self.assertEqual(bytes(image.data), image_bytes)
        self.assertEqual(Product.objects.count(), 1)
