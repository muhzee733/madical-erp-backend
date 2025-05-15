from django.db import models
from users.models import User 

class Drug(models.Model):
    name = models.CharField(max_length=100)
    molecule = models.CharField(max_length=100, blank=True)
    is_schedule_8 = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Prescription(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions_written')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions_received')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

class PrescriptionDrug(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='prescribed_drugs')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)
    instructions = models.TextField()
