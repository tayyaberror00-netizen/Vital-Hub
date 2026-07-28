from django.db import models


class Product(models.Model):
    """
    MODEL layer — a single healthcare product in the Vital Hub store.
    Slug is used as primary key so IDs match the original JS data exactly.
    """

    CATEGORY_CHOICES = [
        ('Monitoring',  'Monitoring'),
        ('Wellness',    'Wellness'),
        ('Wearables',   'Wearables'),
        ('Relaxation',  'Relaxation'),
        ('Pain Relief', 'Pain Relief'),
        ('Fitness',     'Fitness'),
        ('Nutrition',   'Nutrition'),
        ('Dental',      'Dental'),
        ('Safety',      'Safety'),
        ('Mobility',    'Mobility'),
    ]

    # Use the JS slug as PK (e.g. "wrist-bp-monitor")
    id          = models.CharField(max_length=100, primary_key=True)
    name        = models.CharField(max_length=200)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    category    = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    features    = models.JSONField(default=list)
    img         = models.CharField(max_length=500)
    images      = models.JSONField(default=list)
    has_model   = models.BooleanField(default=False)
    model_file  = models.CharField(max_length=500, blank=True)
    has_video   = models.BooleanField(default=False)
    video_file  = models.CharField(max_length=500, blank=True)
    stock       = models.PositiveIntegerField(default=100)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} (Rs. {self.price})'


class ProductLike(models.Model):
    user     = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='liked_products')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='likes')
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table       = 'product_likes'
        unique_together = ('user', 'product')
        ordering        = ['-liked_at']
