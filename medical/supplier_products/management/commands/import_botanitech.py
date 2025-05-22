import pandas as pd
from django.core.management.base import BaseCommand
from supplier_products.models import SupplierProduct

class Command(BaseCommand):
    help = 'Import Botanitech Excel data into SupplierProduct table'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to the Botanitech Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['excel_file']
        df = pd.read_excel(file_path)

        count = 0
        for _, row in df.iterrows():
            SupplierProduct.objects.create(
                supplier_name="Botanitech",
                brand_name=row.get('Trade/Brand name', ''),
                generic_name=row.get('Generic name', ''),
                strength=row.get('Strength', ''),
                dose_form=row.get('Dose form', ''),
                pack_size=row.get('Pack Size', ''),
                packaging_type=row.get('Packaging Type', ''),
                artg_no=row.get('ARTG No ', ''),
                apn=row.get('APN', ''),
                tga_category=str(row.get('TGA Category 1-5', '')),
                access_mechanism=row.get('Access mechanism SAS or Authorised Prescriber', ''),
                poison_schedule=row.get('Poison Schedule', ''),
                storage_information=row.get('Storage Information', '')
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} Botanitech products.'))
