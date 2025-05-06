from rest_framework import serializers
from .models import AppointmentAvailability

class AppointmentAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentAvailability
        fields = '__all__'
        read_only_fields = ['is_booked', 'created_at', 'end_time', 'doctor_id']