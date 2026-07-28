from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = ('name', 'category', 'price', 'stock', 'is_active')
    list_filter    = ('category', 'is_active', 'has_model', 'has_video')
    search_fields  = ('name', 'description')
    list_editable  = ('price', 'stock', 'is_active')
    ordering       = ('category', 'name')

    fieldsets = (
        ('Basic Info',   {'fields': ('id', 'name', 'price', 'category', 'description', 'features')}),
        ('Media',        {'fields': ('img', 'images', 'has_model', 'model_file', 'has_video', 'video_file')}),
        ('Inventory',    {'fields': ('stock', 'is_active')}),
    )
    readonly_fields = ('created_at',)
