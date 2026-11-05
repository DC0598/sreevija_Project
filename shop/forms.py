import re
import uuid

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Order, Product, ProductImage

User = get_user_model()


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email already registered")
        return email


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class CheckoutForm(forms.Form):
    name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=10)
    email = forms.EmailField()
    address = forms.CharField(max_length=300, widget=forms.Textarea(attrs={"rows": 2}))
    city = forms.CharField(max_length=100)
    pincode = forms.CharField(max_length=6)
    payment_method = forms.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not re.fullmatch(r"[6-9]\d{9}", phone):
            raise ValidationError("Enter a valid 10-digit mobile number")
        return phone

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"]
        if not re.fullmatch(r"[1-9]\d{5}", pincode):
            raise ValidationError("Enter a valid 6-digit pincode")
        return pincode


class ProductForm(forms.ModelForm):
    c1 = forms.CharField(widget=forms.TextInput(attrs={"type": "color"}), initial="#e8a0b4")
    c2 = forms.CharField(widget=forms.TextInput(attrs={"type": "color"}), initial="#f3d9a4")
    image_upload = forms.FileField(required=False)

    class Meta:
        model = Product
        fields = (
            "name", "category", "fabric", "color", "occasion", "price", "mrp",
            "rating", "stock", "description", "active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "rating": forms.NumberInput(attrs={"min": 0, "max": 5, "step": "0.1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.colors:
            self.fields["c1"].initial = self.instance.colors[0]
            self.fields["c2"].initial = self.instance.colors[1] if len(self.instance.colors) > 1 else self.instance.colors[0]

    def clean(self):
        cleaned = super().clean()
        for field in ("c1", "c2"):
            color = cleaned.get(field, "")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                self.add_error(field, "Enter a valid hex color.")
        image = cleaned.get("image_upload")
        if image:
            header = image.read(12)
            image.seek(0)
            if header.startswith(b"\xff\xd8\xff"):
                image.content_type = "image/jpeg"
            elif header.startswith(b"\x89PNG\r\n\x1a\n"):
                image.content_type = "image/png"
            elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                image.content_type = "image/webp"
            else:
                self.add_error("image_upload", "Only JPG, PNG, or WEBP images are allowed.")
            if image.size > 4 * 1024 * 1024:
                self.add_error("image_upload", "Image must be 4 MB or smaller.")
        if cleaned.get("price") is not None and cleaned.get("mrp") is not None:
            if cleaned["mrp"] < cleaned["price"]:
                self.add_error("mrp", "MRP must be equal to or greater than the price.")
        for field in ("price", "mrp", "stock"):
            if cleaned.get(field) is not None and cleaned[field] > 10_000_000:
                self.add_error(field, "Enter a value no greater than 10,000,000.")
        if cleaned.get("rating") is not None and not 0 <= cleaned["rating"] <= 5:
            self.add_error("rating", "Rating must be between 0 and 5.")
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        product.colors = [self.cleaned_data["c1"], self.cleaned_data["c2"]]
        uploaded = self.cleaned_data.get("image_upload")
        if uploaded:
            ext = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
            }[uploaded.content_type]
            name = f"{uuid.uuid4().hex}.{ext}"
            ProductImage.objects.create(
                name=name,
                content_type=uploaded.content_type,
                data=uploaded.read(),
            )
            product.image_name = name
        if commit:
            product.save()
        return product


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    payment_status = forms.ChoiceField(choices=Order.PAYMENT_STATUS_CHOICES)
