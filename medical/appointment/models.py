import uuid
from django.db import models
from django.conf import settings

class AppointmentAvailability(models.Model):
    SLOT_TYPE_CHOICES = [
        ("short", "Short (15 minutes)"),
        ("long", "Long (30 minutes)")
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availabilities")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    slot_type = models.CharField(max_length=10, choices=SLOT_TYPE_CHOICES)
    timezone = models.CharField(max_length=100)
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("doctor", "start_time")
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.doctor.email} | {self.start_time} - {self.end_time}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("booked", "Booked"),
        ("cancelled_by_patient", "Cancelled by Patient"),
        ("cancelled_by_doctor", "Cancelled by Doctor"),
        ("cancelled_by_admin", "Cancelled by Admin"),
        ("rescheduled", "Rescheduled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    availability = models.OneToOneField(AppointmentAvailability, on_delete=models.CASCADE, related_name="appointment")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="booked")
    booked_at = models.DateTimeField(auto_now_add=True)
    rescheduled_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    extended_info = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_appointments', on_delete=models.SET_NULL, null=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='updated_appointments', on_delete=models.SET_NULL, null=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.patient.email} -> {self.availability.doctor.email} [{self.status}]"


class AppointmentActionLog(models.Model):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("cancelled", "Cancelled"),
        ("rescheduled", "Rescheduled"),
        ("completed", "Completed"),
        ("no_show", "No Show"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="logs")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action_type} on {self.appointment} by {self.performed_by}"
