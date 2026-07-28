from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    extra  = 0
    fields = ('product_id', 'name', 'price', 'quantity', 'img')
    readonly_fields = ('product_id', 'name', 'price', 'quantity', 'img')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'status', 'total', 'created_at')
    list_filter   = ('status',)
    search_fields = ('user__email', 'shipping_name', 'shipping_email')
    list_editable = ('status',)
    ordering      = ('-created_at',)
    inlines       = [OrderItemInline]
    readonly_fields = ('subtotal', 'shipping_cost', 'total', 'created_at', 'updated_at')

    fieldsets = (
        ('Order Info',  {'fields': ('user', 'status')}),
        ('Shipping',    {'fields': ('shipping_name', 'shipping_email', 'shipping_address')}),
        ('Financials',  {'fields': ('subtotal', 'shipping_cost', 'total')}),
        ('Timestamps',  {'fields': ('created_at', 'updated_at')}),
    )
