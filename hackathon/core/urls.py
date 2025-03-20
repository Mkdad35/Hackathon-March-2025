from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_view, name='search'),
    path('get-ecommerce/', views.get_ecommerce_sites, name='get_ecommerce'),
    path('collect-stores/', views.collect_stores, name='collect_stores'),
    path('scrape-stores/', views.scrape_stores, name='scrape_stores'),
    path('solo-scrape/', views.solo_scrape, name='solo_scrape'),
    path('product/<str:product_data>/', views.product_details, name='product_details'),
] 