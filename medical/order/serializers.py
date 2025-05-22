from rest_framework import serializers
from .models import Order
from appointment.models import AppointmentAvailability


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentAvailability
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(source='appointment.start_time', format='%H:%M:%S', read_only=True)
    appointment_date = serializers.DateField(source='appointment.date', format='%Y-%m-%d', read_only=True)
    appointment = AppointmentSerializer(read_only=True)
    patient_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'amount', 'appointment_date', 'start_time', 'created_at', 'status', 'appointment', 'patient_id']
