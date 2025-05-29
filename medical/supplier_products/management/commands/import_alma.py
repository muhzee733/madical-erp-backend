import pandas as pd
from django.core.management.base import BaseCommand
from supplier_products.models import SupplierProduct
from decimal import Decimal

class Command(BaseCommand):
    help = 'Import Alma Excel data (Sheet1 only) into SupplierProduct table'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Alma Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        df = pd.read_excel(file_path, sheet_name='Sheet1')

        # Normalize and clean
        df['Alma'] = df['Alma'].astype(str).str.strip()
        section_headers = ['el camino', 'beta', 'heritage']
        df = df[df['Alma'].notna()]
        df = df[~df['Alma'].str.lower().isin(section_headers)]

        count = 0
        for _, row in df.iterrows():
            full_name = row.get('Alma', '').strip()
            brand_name, product_name = self.split_brand_and_product(full_name)

            SupplierProduct.objects.create(
                supplier_name="Alma",
                brand_name=brand_name,
                product_name=product_name,
                generic_name=row.get('Heritage', ''),
                strength=self.combine_thc_cbd(row),
                dose_form='Dried Flower',
                strain_type=row.get('Strain', ''),
                cultivar=row.get('Cultiva', ''),
                poison_schedule=row.get('Schedule', ''),
                tga_category=str(row.get('Category', '')),
                wholesale_price=self.to_decimal(row.get('Wholesale')),
                retail_price=self.to_decimal(row.get('RRP')),
                pack_size=str(row.get('Quantity', '')).strip()
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} Alma products.'))

    def split_brand_and_product(self, name):
        name = name.strip()
        for brand in ['Alma', 'El Camino', 'Beta']:
            if name.lower().startswith(brand.lower()):
                return brand, name[len(brand):].strip()
        return '', name  # fallback

    def combine_thc_cbd(self, row):
        thc = str(row.get('THC', '')).replace('THC', '').strip()
        cbd = str(row.get('CBD', '')).replace('CBD', '').strip()
        if thc and cbd:
            return f"THC {thc} / CBD {cbd}"
        elif thc:
            return f"THC {thc}"
        elif cbd:
            return f"CBD {cbd}"
        return ""

    def to_decimal(self, value):
        try:
            return Decimal(str(value).replace('$', '').strip())
        except:
            return None
