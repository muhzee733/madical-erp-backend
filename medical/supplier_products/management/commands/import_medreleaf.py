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
                    supplier_name="MedReleaf",
                    brand_name=row.get('Brand', ''),
                    generic_name=row.get('Product', ''),
                    dose_form=sheet_name,
                    strain_type=row.get(df.columns[2], ''),  # Indica/Sativa/Hybrid column
                    cultivar=row.get('Cultivar', ''),
                    strength=self.combine_thc_cbd(row),
                    tga_category=str(row.get('TGA Cat', '')),
                    retail_price=row.get('Retail', None),
                    wholesale_price=row.get('Wholesale', None),
                    pack_size=row.get('Size', '')
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
