from django.db import models
from django.utils import timezone
from users.models import User


class Drug(models.Model):
    pbs_code = models.CharField(max_length=10, unique=True, default="UNKNOWN")
    drug_name = models.CharField(max_length=100, blank=True, null=True)
    brand_name = models.CharField(max_length=100, blank=True, null=True)
    form = models.CharField(max_length=50, blank=True, null=True)
    strength = models.CharField(max_length=50, blank=True, null=True)
    schedule_code = models.CharField(max_length=10, blank=True, null=True)
    program_code = models.CharField(max_length=10, blank=True, null=True)
    manufacturer_code = models.CharField(max_length=100, blank=True, null=True)
    max_prescribable_pack = models.CharField(max_length=50, blank=True, null=True)
    number_of_repeats = models.IntegerField(default=0)
    container = models.CharField(max_length=100, blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    dangerous_drug_fee_code = models.CharField(max_length=10, blank=True, null=True)
    electronic_chart_eligible = models.BooleanField(default=False)
    infusible_indicator = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.CharField(max_length=100, blank=True, null=True)
    updated_by = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.drug_name} ({self.pbs_code})"


class Prescription(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions_written')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions_received')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    signature_image = models.ImageField(upload_to='signatures/', null=True, blank=True)  # doctor sign
    is_final = models.BooleanField(default=False)

    def __str__(self):
        return f"Rx by Dr. {self.doctor.get_full_name()} for {self.patient.get_full_name()} on {self.created_at.date()}"

    def has_schedule_8(self):
        return any(item.drug.is_schedule_8 for item in self.prescribed_drugs.all())


class PrescriptionDrug(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='prescribed_drugs')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)
    instructions = models.TextField()
    quantity = models.PositiveIntegerField(default=1)
    repeats = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.drug.name} for Rx#{self.prescription.id}"
