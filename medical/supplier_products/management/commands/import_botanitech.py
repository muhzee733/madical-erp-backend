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
            raw_product_name = row.get('Trade/Brand name', '') or ''
            parsed_strain_type, parsed_cultivar = self.parse_product_name(raw_product_name)

            SupplierProduct.objects.create(
                supplier_name = "Cann Group Limited",
                brand_name = "Botanitech",
                product_name = raw_product_name,
                generic_name = row.get('Generic name', '') or None,
                strength = row.get('Strength', '') or None,
                dose_form = row.get('Dose form', '') or None,
                pack_size = row.get('Pack Size', '') or None,
                packaging_type = row.get('Packaging Type', '') or None,
                artg_no = str(row.get('ARTG No ', '')).strip() or None,
                apn = str(row.get('APN', '')).strip() or None,
                tga_category = str(row.get('TGA Category 1-5', '')).strip() or None,
                access_mechanism = row.get('Access mechanism SAS or Authorised Prescriber', '') or None,
                poison_schedule = row.get('Poison Schedule', '') or None,
                storage_information = row.get('Storage Information', '') or None,
                strain_type = parsed_strain_type,
                cultivar = parsed_cultivar,
                wholesale_price = None,
                retail_price = None
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} Botanitech products.'))

    def parse_product_name(self, name):
        """
        Attempts to extract strain_type and cultivar from product_name.
        e.g. 'INC T10 Mango Mint Northern Lights' → ('Indica', 'Mango Mint Northern Lights')
        """
        name = name.strip()
        strain_type = None
        cultivar = None

        if name.upper().startswith("INC"):
            strain_type = "Indica"
        elif name.upper().startswith("SAT"):
            strain_type = "Sativa"
        elif name.upper().startswith("HYB"):
            strain_type = "Hybrid"

        parts = name.split(" ", 2)
        if len(parts) >= 3:
            cultivar = parts[2].strip()

        return strain_type, cultivar
