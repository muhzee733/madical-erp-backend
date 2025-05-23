# Generated by Django 5.2 on 2025-05-22 05:15

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SupplierProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('supplier_name', models.CharField(max_length=255)),
                ('brand_name', models.CharField(blank=True, max_length=255, null=True)),
                ('generic_name', models.TextField(blank=True, null=True)),
                ('strength', models.CharField(blank=True, max_length=100, null=True)),
                ('dose_form', models.CharField(blank=True, max_length=100, null=True)),
                ('pack_size', models.CharField(blank=True, max_length=100, null=True)),
                ('packaging_type', models.CharField(blank=True, max_length=100, null=True)),
                ('artg_no', models.CharField(blank=True, max_length=100, null=True)),
                ('apn', models.CharField(blank=True, max_length=100, null=True)),
                ('tga_category', models.CharField(blank=True, max_length=100, null=True)),
                ('access_mechanism', models.CharField(blank=True, max_length=255, null=True)),
                ('poison_schedule', models.CharField(blank=True, max_length=100, null=True)),
                ('storage_information', models.TextField(blank=True, null=True)),
                ('strain_type', models.CharField(blank=True, max_length=100, null=True)),
                ('cultivar', models.CharField(blank=True, max_length=255, null=True)),
                ('wholesale_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('retail_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
