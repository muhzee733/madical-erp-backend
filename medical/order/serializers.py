from rest_framework import serializers
from .models import Order
from appointment.models import Appointment
from appointment.serializers import AppointmentSerializer


class OrderSerializer(serializers.ModelSerializer):
    start_time = serializers.SerializerMethodField()
    appointment_date = serializers.SerializerMethodField()
    appointment = AppointmentSerializer(read_only=True)
    patient_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'amount', 'appointment_date', 'start_time', 'created_at', 'status', 'appointment', 'patient_id']

    def get_start_time(self, obj):
        try:
            return obj.appointment.availability.start_time.time()
        except Exception:
            return None

    def get_appointment_date(self, obj):
        try:
            return obj.appointment.availability.start_time.date()
        except Exception:
            return None
