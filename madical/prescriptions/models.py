from django.db import models
from users.models import User

class Drug(models.Model):
    name = models.CharField(max_length=100)
    molecule = models.CharField(max_length=100, blank=True)
    form = models.CharField(max_length=50, blank=True)  # e.g., oil, capsule
    strength = models.CharField(max_length=100, blank=True)  # e.g., 10mg/ml
    is_schedule_8 = models.BooleanField(default=False)
    manufacturer = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.strength})"


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
