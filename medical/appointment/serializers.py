from rest_framework import serializers
from .models import AppointmentAvailability, Appointment, AppointmentActionLog
from django.utils.timezone import now

class AppointmentAvailabilitySerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(write_only=True, required=False, default='Australia/Brisbane')

    class Meta:
        model = AppointmentAvailability
        fields = '__all__'
        read_only_fields = ['id', 'is_booked', 'created_at', 'doctor']

    def validate(self, data):
        request = self.context.get("request")
        timezone_str = request.data.get("timezone", "Australia/Brisbane")
        tz = ZoneInfo(timezone_str)

        start = data['start_time']
        end = data['end_time']

        # Convert to timezone-aware UTC datetime if naive
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            data['start_time'] = start
        if end.tzinfo is None:
            end = end.replace(tzinfo=tz).astimezone(ZoneInfo("UTC"))
            data['end_time'] = end

        # Now validate after normalization
        if start >= end:
            raise serializers.ValidationError("End time must be after start time.")
        if start < now():
            raise serializers.ValidationError("Start time must be in the future.")

        return data

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['id', 'booked_at', 'status', 'rescheduled_from', 'patient']  

    def validate(self, data):
        availability = data.get('availability')
        if availability.is_booked:
            raise serializers.ValidationError("This slot is already booked.")

        request = self.context.get('request')
        patient = request.user if request else None

        new_start = availability.start_time
        new_end = availability.end_time

        overlapping = Appointment.objects.filter(
            patient=patient,
            availability__start_time__lt=new_end,
            availability__end_time__gt=new_start,
        ).exclude(status__in=['cancelled_by_patient', 'cancelled_by_doctor'])

        if overlapping.exists():
            raise serializers.ValidationError("You already have an appointment during this time.")

        return data

    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class AppointmentActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentActionLog
        fields = '__all__'
        read_only_fields = ['id', 'performed_at']
