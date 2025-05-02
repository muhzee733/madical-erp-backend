# models.py
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from appointment.models import AppointmentAvailability
import uuid

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    appointment = models.ForeignKey(AppointmentAvailability, on_delete=models.CASCADE)
    payment_intent = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending') 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
