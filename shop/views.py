import re

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, LoginForm, OrderStatusForm, ProductForm, RegistrationForm
from .models import NewsletterSubscriber, Order, OrderItem, Product, ProductImage, Wishlist

FREE_SHIP = 1999
SHIP_FEE = 99
CATEGORY_IMAGES = {
    "Kanjivaram": "https://images.unsplash.com/photo-1641699862936-be9f49b1c38d?auto=format&fit=crop&w=900&q=85",
    "Silk": "https://images.unsplash.com/photo-1650324371896-f0b4bc2238dd?auto=format&fit=crop&w=900&q=85",
    "Dharmavaram": "https://images.unsplash.com/photo-1635452141122-51866572620c?auto=format&fit=crop&w=900&q=85",
    "Bridal": "https://images.unsplash.com/photo-1778148046511-27141f5f01ae?auto=format&fit=crop&w=900&q=85",
}
DEFAULT_IMAGE = CATEGORY_IMAGES["Silk"]
User = get_user_model()


def product_image_url(product):
    if product.image_name:
        return reverse("product_image", args=[product.image_name])
    return CATEGORY_IMAGES.get(product.category, DEFAULT_IMAGE)


def safe_redirect(request, destination, fallback):
    if destination and url_has_allowed_host_and_scheme(
        destination,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destination)
    return redirect(fallback)


def product_card(product):
    return {
        "product": product,
        "image_url": product_image_url(product),
    }


def cart_lines(request, lock=False):
    cart = request.session.get("cart", {})
    ids = []
    for key in cart:
        try:
            ids.append(int(key))
        except (TypeError, ValueError):
            continue
    queryset = Product.objects.filter(pk__in=ids, active=True)
    if lock:
        queryset = queryset.select_for_update()
    products = {product.pk: product for product in queryset}
    lines = []
    for key, quantity in cart.items():
        try:
            product_id = int(key)
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        product = products.get(product_id)
        if product and quantity > 0:
            lines.append({"product": product, "qty": min(quantity, 20)})
    return lines


def cart_summary(lines):
    subtotal = sum(line["product"].price * line["qty"] for line in lines)
    shipping = SHIP_FEE if subtotal and subtotal < FREE_SHIP else 0
    return {"subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping}


def home(request):
    products = Product.objects.filter(active=True)
    bestsellers = products.order_by("-rating", "-created_at")[:4]
    return render(
        request,
        "shop/home.html",
        {
            "bestsellers": [product_card(product) for product in bestsellers],
            "categories": [
                {"title": "Silk Sarees", "category": "Silk", "image": CATEGORY_IMAGES["Kanjivaram"]},
                {"title": "Handloom Sarees", "category": "Dharmavaram", "image": CATEGORY_IMAGES["Silk"]},
                {"title": "Festive Collection", "category": "Bridal", "image": CATEGORY_IMAGES["Bridal"]},
            ],
        },
    )


def product_list(request):
    products = Product.objects.filter(active=True)
    filters = {
        "category": request.GET.get("category", "").strip(),
        "fabric": request.GET.get("fabric", "").strip(),
        "occasion": request.GET.get("occasion", "").strip(),
        "q": request.GET.get("q", "").strip(),
        "sort": request.GET.get("sort", "popular"),
        "sale": request.GET.get("sale", ""),
    }
    if filters["category"]:
        products = products.filter(category=filters["category"])
    if filters["fabric"]:
        products = products.filter(fabric=filters["fabric"])
    if filters["occasion"]:
        products = products.filter(occasion=filters["occasion"])
    if filters["q"]:
        from django.db.models import Q

        products = products.filter(
            Q(name__icontains=filters["q"])
            | Q(fabric__icontains=filters["q"])
            | Q(color__icontains=filters["q"])
            | Q(category__icontains=filters["q"])
        )
    try:
        max_price = max(1000, min(20000, int(request.GET.get("max", 20000))))
    except (TypeError, ValueError):
        max_price = 20000
    products = products.filter(price__lte=max_price)
    if filters["sale"]:
        products = [p for p in products if p.discount_percent >= 20]
    sort_options = {
        "popular": ("-rating", "-created_at"),
        "new": ("-created_at",),
        "low": ("price",),
        "high": ("-price",),
    }
    if filters["sort"] not in sort_options:
        filters["sort"] = "popular"
    if isinstance(products, list):
        if filters["sort"] == "popular":
            products.sort(key=lambda product: (product.rating, product.created_at), reverse=True)
        elif filters["sort"] == "new":
            products.sort(key=lambda product: product.created_at, reverse=True)
        elif filters["sort"] == "low":
            products.sort(key=lambda product: product.price)
        else:
            products.sort(key=lambda product: product.price, reverse=True)
        product_cards = [product_card(product) for product in products]
    else:
        product_cards = [product_card(product) for product in products.order_by(*sort_options[filters["sort"]])]
    all_products = Product.objects.filter(active=True)
    return render(
        request,
        "shop/product_list.html",
        {
            "products": product_cards,
            "filters": filters,
            "max_price": max_price,
            "categories": all_products.order_by("category").values_list("category", flat=True).distinct(),
            "fabrics": all_products.order_by("fabric").values_list("fabric", flat=True).distinct(),
            "occasions": all_products.order_by("occasion").values_list("occasion", flat=True).distinct(),
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    related = Product.objects.filter(active=True, category=product.category).exclude(pk=pk)[:4]
    wishlisted = request.user.is_authenticated and Wishlist.objects.filter(
        user=request.user, product=product
    ).exists()
    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
            "image_url": product_image_url(product),
            "related": [product_card(item) for item in related],
            "wishlisted": wishlisted,
        },
    )


def story(request):
    return render(request, "shop/story.html")


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    try:
        quantity = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        quantity = 0
    if quantity < 1 or quantity > 20:
        messages.error(request, "Select a valid quantity.")
        return redirect("product", pk=pk)
    cart = request.session.get("cart", {})
    current = int(cart.get(str(pk), 0))
    if current + quantity > product.stock:
        messages.error(request, f"Only {product.stock} left in stock.")
        return redirect("product", pk=pk)
    cart[str(pk)] = current + quantity
    request.session["cart"] = cart
    if request.POST.get("next") == "checkout":
        return redirect("checkout")
    messages.success(request, "Added to cart.")
    return safe_redirect(request, request.POST.get("return_to"), "cart")


@require_POST
def cart_update(request, pk):
    cart = request.session.get("cart", {})
    if str(pk) not in cart:
        return redirect("cart")
    action = request.POST.get("action")
    product = Product.objects.filter(pk=pk, active=True).first()
    if action == "remove" or not product:
        cart.pop(str(pk), None)
    else:
        try:
            quantity = int(request.POST.get("qty", cart[str(pk)]))
        except (TypeError, ValueError):
            quantity = 0
        if quantity <= 0:
            cart.pop(str(pk), None)
        elif quantity > 20 or quantity > product.stock:
            messages.error(request, f"Only {product.stock} left in stock.")
        else:
            cart[str(pk)] = quantity
    request.session["cart"] = cart
    return redirect("cart")


def cart(request):
    lines = cart_lines(request)
    return render(
        request,
        "shop/cart.html",
        {"lines": [dict(line, image_url=product_image_url(line["product"])) for line in lines], **cart_summary(lines)},
    )


@require_POST
def wishlist_toggle(request, pk):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to use your wishlist.")
        return redirect(f"{reverse('login')}?next={reverse('wishlist')}")
    product = get_object_or_404(Product, pk=pk, active=True)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        wishlist_item.delete()
    return safe_redirect(request, request.POST.get("return_to"), "wishlist")


@login_required
def wishlist(request):
    products = Product.objects.filter(
        wishlist__user=request.user, active=True
    ).distinct()
    return render(
        request,
        "shop/wishlist.html",
        {"products": [product_card(product) for product in products]},
    )


def checkout(request):
    lines = cart_lines(request)
    if not lines:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "name": request.user.first_name or request.user.username,
            "email": request.user.email,
        }
    form = CheckoutForm(request.POST or None, initial=initial)
    totals = cart_summary(lines)
    if request.method == "POST" and form.is_valid():
        cart_data = request.session.get("cart", {})
        try:
            with transaction.atomic():
                locked_lines = cart_lines(request, lock=True)
                if len(locked_lines) != len(lines):
                    raise ValueError("A product in your cart is no longer available.")
                subtotal = 0
                for line in locked_lines:
                    quantity = min(int(cart_data.get(str(line["product"].pk), 0)), 20)
                    if quantity < 1:
                        raise ValueError("Your cart has changed. Please review it and try again.")
                    if line["product"].stock < quantity:
                        raise ValueError(
                            f"Only {line['product'].stock} left of {line['product'].name}."
                        )
                    line["qty"] = quantity
                    subtotal += line["product"].price * quantity
                shipping = 0 if subtotal >= FREE_SHIP else SHIP_FEE
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    subtotal=subtotal,
                    shipping=shipping,
                    total=subtotal + shipping,
                    **form.cleaned_data,
                )
                for line in locked_lines:
                    product = line["product"]
                    quantity = line["qty"]
                    Product.objects.filter(pk=product.pk).update(stock=F("stock") - quantity)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        name=product.name,
                        price=product.price,
                        qty=quantity,
                    )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("cart")
        request.session["cart"] = {}
        return redirect("order_confirmation", order_id=order.pk)
    return render(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "lines": [dict(line, image_url=product_image_url(line["product"])) for line in lines],
            **totals,
        },
    )


@login_required
def orders(request):
    order_list = Order.objects.filter(user=request.user).prefetch_related("items").order_by("-created_at")
    return render(request, "shop/orders.html", {"orders": order_list})


def order_confirmation(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if order.user_id and order.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    return render(request, "shop/order_confirmation.html", {"order": order})


def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            validate_password(form.cleaned_data["password"])
        except ValidationError as exc:
            form.add_error("password", exc)
        else:
            email = form.cleaned_data["email"]
            user = User.objects.create_user(
                username=email,
                email=email,
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["name"].strip(),
            )
            login(request, user)
            return redirect("home")
    return render(request, "shop/auth_form.html", {"form": form, "register": True})


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"].strip().lower()
        user = authenticate(
            request,
            username=identifier,
            password=form.cleaned_data["password"],
        )
        if user is None:
            form.add_error(None, "Invalid email or password.")
        else:
            login(request, user)
            next_url = request.POST.get("next", "")
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("manage" if user.is_staff else "home")
    return render(
        request,
        "shop/auth_form.html",
        {"form": form, "register": False, "next": request.GET.get("next", "")},
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


def delivery_check(request):
    pin = request.GET.get("pin", "").strip()
    if not re.fullmatch(r"[1-9]\d{5}", pin):
        return render(request, "shop/delivery_check.html", {"pin": pin, "error": "Enter a valid 6-digit pincode."})
    return render(request, "shop/delivery_check.html", {"pin": pin, "days": "4–6"})


@require_POST
def newsletter(request):
    email = request.POST.get("email", "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        messages.error(request, "Enter a valid email address.")
    else:
        NewsletterSubscriber.objects.get_or_create(email=email)
        messages.success(request, "Thanks for subscribing!")
    return safe_redirect(request, request.META.get("HTTP_REFERER"), "home")


def product_image(request, name):
    if not re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|png|webp)", name):
        raise Http404
    image = get_object_or_404(ProductImage, pk=name)
    response = HttpResponse(bytes(image.data), content_type=image.content_type)
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    response["X-Content-Type-Options"] = "nosniff"
    return response


staff_required = user_passes_test(lambda user: user.is_authenticated and user.is_staff)


@staff_required
def manage(request):
    orders_list = Order.objects.prefetch_related("items").order_by("-created_at")
    products = Product.objects.order_by("-created_at")
    stats = {
        "orders": Order.objects.count(),
        "revenue": Order.objects.exclude(status="Cancelled").aggregate(total=Sum("total"))["total"] or 0,
        "products": Product.objects.filter(active=True).count(),
        "low_stock": Product.objects.filter(active=True, stock__lte=3).count(),
    }
    return render(
        request,
        "shop/manage.html",
        {
            "stats": stats,
            "orders": orders_list,
            "products": [dict(product=product, image_url=product_image_url(product)) for product in products],
        },
    )


@staff_required
def manage_product(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, "Product saved.")
        return redirect("manage")
    return render(request, "shop/product_form.html", {"form": form, "product": instance})


@staff_required
@require_POST
def manage_product_visibility(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.active = not product.active
    product.save(update_fields=["active"])
    messages.success(request, "Product visibility updated.")
    return redirect("manage")


@staff_required
@require_POST
def manage_order(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        form = OrderStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["status"]
            if order.status == "Cancelled" and new_status != "Cancelled":
                messages.error(request, "Cancelled orders cannot be reopened.")
                return redirect("manage")
            if new_status == "Cancelled" and order.status != "Cancelled":
                items = list(order.items.select_for_update())
                for item in items:
                    if item.product_id:
                        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.qty)
            order.status = new_status
            order.payment_status = form.cleaned_data["payment_status"]
            order.save(update_fields=["status", "payment_status"])
            messages.success(request, "Order updated.")
        else:
            messages.error(request, "Choose valid order and payment statuses.")
    return redirect("manage")
