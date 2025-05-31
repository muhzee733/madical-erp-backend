import pandas as pd
from django.core.management.base import BaseCommand
from supplier_products.models import SupplierProduct

class Command(BaseCommand):
    help = 'Import Phytoca Product Master spreadsheet into SupplierProduct table'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Phytoca Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        df = df.set_index(df.columns[0]).transpose().reset_index()
        df.columns.name = None

        count = 0
        for _, row in df.iterrows():
            SupplierProduct.objects.create(
                supplier_name = "Phytoca",
                brand_name = row.get('Product Brand', '') or None,
                product_name = row.get('Product Name', '') or None,
                generic_name = row.get('TGA Trade name', '') or None,
                dose_form = row.get('TGA Dosage Form', '') or None,
                pack_size = row.get('Product Size (grams, ml, pieces)', '') or None,
                poison_schedule = str(row.get('Product Schedule', '')).strip() or None,
                tga_category = str(row.get('TGA Category', '')).strip() or None,
                strain_type = row.get('Strain Type (multichoice)', '') or None,
                cultivar = row.get('Strain Name', '') or None,
                strength = self.combine_strength(row),
                wholesale_price = self.to_decimal(row.get('Recommended Wholesale Price')),
                retail_price = self.to_decimal(row.get('Recommended Retail Price')),
                artg_no = None,
                apn = None,
                packaging_type = None,
                access_mechanism = None,
                storage_information = None,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} Phytoca products.'))

    def combine_strength(self, row):
        thc = str(row.get('THC mg/ml/piece and/or %', '')).strip()
        cbd = str(row.get('CBD mg/ml/piece and/or %', '')).strip()
        note = str(row.get('Cannabinoids', '')).strip()

        parts = []
        if thc and thc.lower() != 'nan':
            parts.append(f"THC {thc}")
        if cbd and cbd.lower() != 'nan':
            parts.append(f"CBD {cbd}")
        strength = " / ".join(parts)

        if note and note.lower() != 'nan':
            strength = f"{strength} ({note})" if strength else f"({note})"

        return strength or None

    def to_decimal(self, value):
        try:
            return float(value) if pd.notna(value) else None
        except (ValueError, TypeError):
            return None
