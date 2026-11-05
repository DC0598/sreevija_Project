from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="shop"),
    path("product/<int:pk>/", views.product_detail, name="product"),
    path("story/", views.story, name="story"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.orders, name="orders"),
    path("orders/placed/<str:order_id>/", views.order_confirmation, name="order_confirmation"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("delivery-check/", views.delivery_check, name="delivery_check"),
    path("newsletter/", views.newsletter, name="newsletter"),
    path("uploads/<str:name>", views.product_image, name="product_image"),
    path("manage/", views.manage, name="manage"),
    path("manage/orders/", views.manage_orders, name="manage_orders"),
    path("manage/products/add/", views.manage_product, name="manage_product_add"),
    path("manage/products/<int:pk>/", views.manage_product, name="manage_product"),
    path("manage/products/<int:pk>/visibility/", views.manage_product_visibility, name="manage_product_visibility"),
    path("manage/orders/<str:order_id>/", views.manage_order, name="manage_order"),
]
