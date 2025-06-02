from rest_framework import serializers
from .models import AppointmentAvailability, Appointment, AppointmentActionLog
from django.utils.timezone import now
from users.serializers import DoctorProfileSerializer, PatientProfileSerializer, UserSerializer

class AppointmentAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentAvailability
        fields = '__all__'
        read_only_fields = ['id', 'is_booked', 'created_at', 'doctor']

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        if data['start_time'] < now():
            raise serializers.ValidationError("Start time must be in the future.")
        return data

class AppointmentSerializer(serializers.ModelSerializer):
    patient = UserSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'availability',
            'patient',
            'status',
            'booked_at',
            'rescheduled_from',
            'extended_info',
            'note',
            'created_by',
            'updated_by',
            'is_deleted'
        ]
        read_only_fields = [
            'id',
            'patient',
            'status',
            'booked_at',
            'rescheduled_from',
            'created_by',
            'updated_by',
            'is_deleted'
        ]

    def update(self, instance, validated_data):
        user = self.context['request'].user
        allowed_fields = []

        if user.role == 'patient':
            allowed_fields = ['note', 'extended_info']
        elif user.role == 'doctor':
            allowed_fields =['note', 'extended_info', 'availability', 'status']
        elif user.role == 'admin':
            allowed_fields = ['note', 'extended_info', 'availability', 'status']

        updated_fields = []
        changes = []

        for field in allowed_fields:
            if field in validated_data:
                old_value = getattr(instance, field)
                new_value = validated_data[field]
                
                if old_value != new_value:
                    setattr(instance, field, new_value)
                    updated_fields.append(field)
                    changes.append(f"{field}: '{old_value}' → '{new_value}'")

        if updated_fields:
            instance.updated_by = user
            instance.save()

            AppointmentActionLog.objects.create(
                appointment=instance,
                action_type="updated",
                performed_by=user,
                note="; ".join(changes)
            )

        return instance

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

class AppointmentPartyInfoSerializer(serializers.Serializer):
    patient_user = UserSerializer()
    patient_profile = PatientProfileSerializer()
    doctor_user = UserSerializer()
    doctor_profile = DoctorProfileSerializer()
