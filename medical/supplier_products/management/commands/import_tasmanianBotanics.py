import pandas as pd
from django.core.management.base import BaseCommand
from supplier_products.models import SupplierProduct
from decimal import Decimal


class Command(BaseCommand):
    help = 'Import Tasmanian Botanics Excel data into SupplierProduct table'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        df = pd.read_excel(file_path, sheet_name='Tasmanian Botanics Product List')

        count = 0
        for _, row in df.iterrows():
            try:
                SupplierProduct.objects.create(
                    supplier_name="Tasmanian Botanics",
                    brand_name=row.get('Brand', '').strip(),
                    product_name=row.get('Product Name', '').strip(),
                    strength=row.get('Active Ingredients', '').strip(),
                    dose_form=row.get('Dose Form', '').strip(),
                    pack_size=row.get('Pack Size', '').strip(),
                    packaging_type=row.get('Packaging Type', '').strip(),
                    poison_schedule=self.clean_schedule(row.get('Drug Schedule', '')),
                    tga_category=self.clean_schedule(row.get('TGA Category', '')),
                    wholesale_price=self.to_decimal(row.get('Wholesale Price (exc GST)', '')),
                    retail_price=self.to_decimal(row.get('RRP (inc GST)', '')),
                    access_mechanism=row.get('How is it available?', '').strip(),
                    artg_no=str(row.get('ARTG ID', '')).strip() or None,
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skipped row due to error: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} Tasmanian Botanics products.'))

    def to_decimal(self, value):
        try:
            return Decimal(str(value).replace('$', '').strip())
        except:
            return None

    def clean_schedule(self, value):
        if pd.isna(value):
            return None
        return ''.join(filter(str.isdigit, str(value)))
