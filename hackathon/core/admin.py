from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'category', 'url')
    list_filter = ('country', 'category')
    search_fields = ('name', 'country')
    ordering = ('country', 'category', 'name')
