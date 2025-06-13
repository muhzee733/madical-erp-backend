from celery import shared_task
from .models import Appointment

def _expire_appointment_logic(appointment):
    if appointment.status == "pending" and appointment.availability.is_booked:
        appointment.status = "payment_expired"
        appointment.availability.is_booked = False
        appointment.availability.save()
        appointment.save()

@shared_task
def expire_pending_appointment(appointment_id):
    try:
        appointment = Appointment.objects.select_related('availability').get(id=appointment_id)
        _expire_appointment_logic(appointment)
    except Appointment.DoesNotExist:
        pass
