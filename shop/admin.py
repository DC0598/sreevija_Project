from django.contrib import admin

from .models import NewsletterSubscriber, Order, OrderItem, Product, ProductImage, Wishlist

admin.site.register(Product)
admin.site.register(Wishlist)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ProductImage)
admin.site.register(NewsletterSubscriber)
