def storefront(request):
    cart = request.session.get("cart", {})
    wishlist_ids = set()
    if request.user.is_authenticated:
        from .models import Wishlist

        wishlist_ids = set(
            Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    return {
        "cart_count": sum(
            quantity for quantity in cart.values() if isinstance(quantity, int) and quantity > 0
        ),
        "wishlist_ids": wishlist_ids,
    }
