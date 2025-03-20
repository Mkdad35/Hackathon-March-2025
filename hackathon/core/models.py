from django.db import models

# Create your models here.

class Store(models.Model):
    CATEGORY_CHOICES = [
        ('fashion', 'Fashion & Accessories'),
        ('electronics', 'Electronics & Technology'),
        ('beauty', 'Beauty & Cosmetics'),
        ('sports', 'Sports & Fitness'),
        ('home', 'Home & Garden'),
        ('books', 'Books & Stationery'),
        ('toys', 'Toys & Games'),
        ('automotive', 'Automotive'),
        ('pets', 'Pet Supplies'),
        ('luxury', 'Luxury & Watches'),
        ('music', 'Music & Instruments')
    ]

    name = models.CharField(max_length=200, verbose_name="Store Name")
    url = models.URLField(verbose_name="Website URL")
    country = models.CharField(max_length=100, verbose_name="Country")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Category"
    )
    shipping_info = models.TextField(verbose_name="Shipping Information", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ['country', 'category', 'name']
        unique_together = ['name', 'country']  # لمنع تكرار نفس المتجر في نفس الدولة

    def __str__(self):
        return f"{self.name} ({self.country})"
