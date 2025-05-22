from django.db import models

class SupplierProduct(models.Model):
    supplier_name = models.CharField(max_length=255)
    brand_name = models.CharField(max_length=255, blank=True, null=True)
    generic_name = models.TextField(blank=True, null=True)
    strength = models.CharField(max_length=100, blank=True, null=True)
    dose_form = models.CharField(max_length=100, blank=True, null=True)
    pack_size = models.CharField(max_length=100, blank=True, null=True)
    packaging_type = models.CharField(max_length=100, blank=True, null=True)
    artg_no = models.CharField(max_length=100, blank=True, null=True)
    apn = models.CharField(max_length=100, blank=True, null=True)
    tga_category = models.CharField(max_length=100, blank=True, null=True)
    access_mechanism = models.CharField(max_length=255, blank=True, null=True)
    poison_schedule = models.CharField(max_length=100, blank=True, null=True)
    storage_information = models.TextField(blank=True, null=True)
    strain_type = models.CharField(max_length=100, blank=True, null=True)
    cultivar = models.CharField(max_length=255, blank=True, null=True)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.brand_name or self.generic_name or "Unnamed Product"
