import pandas as pd
from django.core.management.base import BaseCommand
from supplier_products.models import SupplierProduct

class Command(BaseCommand):
    help = 'Import MedReleaf Excel data into SupplierProduct table'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the MedReleaf Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        sheets = pd.read_excel(file_path, sheet_name=None)
        total_count = 0

        for sheet_name, df in sheets.items():
            count = 0
            for _, row in df.iterrows():
                SupplierProduct.objects.create(
                    supplier_name = "MedReleaf",
                    brand_name = row.get('Brand', '') or None,
		    product_name = row.get('Product', '') or None,
		    generic_name = None,
		    dose_form = sheet_name,
    		    strain_type = row.get('Strain Type', '') or None,
                    cultivar = row.get('Cultivar', '') or None,
                    strength = self.combine_thc_cbd(row),
                    tga_category = str(row.get('TGA Cat', '') or ''),
                    retail_price = self.to_decimal(row.get('Retail')),
                    wholesale_price = self.to_decimal(row.get('Wholesale')),
                    pack_size = row.get('Size', '') or None,
                    packaging_type = None,
                    artg_no = None,
                    apn = None,
                    access_mechanism = None,
                    poison_schedule = None,
                    storage_information = None
                )
                count += 1
            self.stdout.write(self.style.SUCCESS(f'Imported {count} products from sheet: {sheet_name}'))
            total_count += count

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {total_count} MedReleaf products.'))

    def combine_thc_cbd(self, row):
        thc = row.get('THC', '')
        cbd = row.get('CBD', '')
        if pd.notna(thc) and pd.notna(cbd):
            return f"THC {thc} / CBD {cbd}"
        elif pd.notna(thc):
            return f"THC {thc}"
        elif pd.notna(cbd):
            return f"CBD {cbd}"
        return ""

    def to_decimal(self, value):
        try:
            return float(value) if pd.notna(value) else None
        except (ValueError, TypeError):
            return None
