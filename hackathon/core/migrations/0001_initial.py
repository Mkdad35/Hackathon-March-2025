# Generated by Django 4.2.7 on 2025-03-13 02:41

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Store Name')),
                ('url', models.URLField(verbose_name='Website URL')),
                ('country', models.CharField(max_length=100, verbose_name='Country')),
                ('category', models.CharField(choices=[('fashion', 'Fashion & Accessories'), ('electronics', 'Electronics & Technology'), ('beauty', 'Beauty & Cosmetics'), ('sports', 'Sports & Fitness'), ('home', 'Home & Garden'), ('books', 'Books & Stationery'), ('toys', 'Toys & Games'), ('automotive', 'Automotive'), ('pets', 'Pet Supplies'), ('luxury', 'Luxury & Watches'), ('music', 'Music & Instruments')], max_length=20, verbose_name='Category')),
                ('shipping_info', models.TextField(blank=True, verbose_name='Shipping Information')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Store',
                'verbose_name_plural': 'Stores',
                'ordering': ['country', 'category', 'name'],
                'unique_together': {('name', 'country')},
            },
        ),
    ]
