from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile

def generate_prescription_pdf(prescription):
    html_string = render_to_string('prescriptions/prescription_pdf.html', {
        'prescription': prescription,
        'doctor': prescription.doctor,
        'patient': prescription.patient,
        'items': prescription.prescribed_drugs.all(),
        'supplier_items': prescription.prescribed_supplier_products.all(),
    })

    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(output.name)
        output.seek(0)
        return output.read()
