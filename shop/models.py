import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    fabric = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    occasion = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    mrp = models.PositiveIntegerField()
    rating = models.FloatField(default=4.5)
    stock = models.PositiveIntegerField(default=0)
    colors = models.JSONField(default=list)
    description = models.TextField(blank=True)
    image_name = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        if not self.mrp:
            return 0
        return max(0, round((1 - self.price / self.mrp) * 100))


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "product"), name="unique_user_wishlist_product")
        ]


class Order(models.Model):
    STATUS_CHOICES = [
        ("Placed", "Placed"),
        ("Confirmed", "Confirmed"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Refunded", "Refunded"),
    ]
    PAYMENT_METHOD_CHOICES = [
        ("UPI", "UPI"),
        ("Credit / Debit Card", "Credit / Debit Card"),
        ("Net Banking", "Net Banking"),
        ("Cash on Delivery", "Cash on Delivery"),
    ]

    id = models.CharField(primary_key=True, max_length=10, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10)
    email = models.EmailField()
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(
        max_length=16, choices=PAYMENT_STATUS_CHOICES, default="Pending"
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Placed")
    subtotal = models.PositiveIntegerField()
    shipping = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.pk = "SS" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.pk


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    qty = models.PositiveIntegerField()


class ProductImage(models.Model):
    name = models.CharField(primary_key=True, max_length=64)
    content_type = models.CharField(max_length=32)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
