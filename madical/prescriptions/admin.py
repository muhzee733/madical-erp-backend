from django.contrib import admin
from django.utils.html import format_html
from .models import Prescription, PrescriptionDrug, Drug

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('pbs_code', 'drug_name', 'brand_name', 'is_active')
    search_fields = ('pbs_code', 'drug_name', 'brand_name')
    list_filter = ('is_active', 'schedule_code')


@admin.register(PrescriptionDrug)
class PrescriptionDrugAdmin(admin.ModelAdmin):
    list_display = ['prescription', 'drug', 'dosage', 'quantity', 'repeats']


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'doctor', 'patient', 'created_at', 'is_final', 'pdf_link']
    readonly_fields = ['created_at']

    def pdf_link(self, obj):
        return format_html(
            '<a class="button" href="/prescriptions/pdf/{}/" target="_blank">Download PDF</a>',
            obj.id
        )
    pdf_link.short_description = "Export PDF"
