from django.contrib import admin

from .models import Category, Location, Post, Comments

admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Post)
admin.site.register(Comments)
