from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
User = get_user_model()


class AppointmentAvailability(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'doctor_appointment_availability'

    def __str__(self):
        return f"{self.doctor} - {self.date} ({self.start_time}-{self.end_time})"