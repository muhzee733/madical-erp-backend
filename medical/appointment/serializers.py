from rest_framework import serializers
from .models import AppointmentAvailability, Appointment, AppointmentActionLog
from django.utils.timezone import now
from users.serializers import DoctorProfileSerializer, PatientProfileSerializer, UserSerializer
from .constants import NEW_PATIENT_FEE, RETURNING_PATIENT_FEE, COMPLETED_APPOINTMENT_STATUSES

class AppointmentAvailabilitySerializer(serializers.ModelSerializer):
    doctor = UserSerializer(read_only=True)
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
    availability = AppointmentAvailabilitySerializer(read_only=True)
    availability_id = serializers.PrimaryKeyRelatedField(
        queryset=AppointmentAvailability.objects.all(),
        source='availability',
        write_only=True
    )


    class Meta:
        model = Appointment
        fields = [
            'id',
            'availability',
            'availability_id',
            'patient',
            'status',
            'booked_at',
            'rescheduled_from',
            'extended_info',
            'note',
            'price',
            'is_initial',
            'created_by',
            'updated_by',
            'is_deleted',
        ]
        read_only_fields = [
            'id',
            'patient',
            'booked_at',
            'rescheduled_from',
            'created_by',
            'updated_by',
            'is_deleted',
            'price',
            'is_initial',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['patient'] = user

        # New billing logic: Check if patient has any previous appointments
        # Automatically determine pricing based on patient history
        has_prior_appointments = Appointment.objects.filter(
            patient=user,
            status__in=COMPLETED_APPOINTMENT_STATUSES
        ).exists()

        # Set pricing based on patient history (not appointment type)
        if has_prior_appointments:
            # Returning patient: $50 flat fee regardless of appointment type
            validated_data['is_initial'] = False
            validated_data['price'] = RETURNING_PATIENT_FEE
        else:
            # New patient: $80 flat fee for first-ever appointment
            validated_data['is_initial'] = True
            validated_data['price'] = NEW_PATIENT_FEE

        # Optional fields
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            validated_data['extended_info'] = request.data.get('extended_info')
            validated_data['note'] = request.data.get('note')

        return super().create(validated_data)


    def update(self, instance, validated_data):
        user = self.context['request'].user
        allowed_fields = []

        if user.role == 'patient':
            allowed_fields = ['note', 'extended_info']
        elif user.role == 'doctor':
            allowed_fields = ['note', 'extended_info', 'availability', 'status']
        elif user.role == 'admin':
            allowed_fields = ['note', 'extended_info', 'availability', 'status']

        updated_fields = []
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                updated_fields.append(field)

        if updated_fields:
            instance.updated_by = user
            instance.save()

            AppointmentActionLog.objects.create(
                appointment=instance,
                action_type="updated",
                performed_by=user,
                note=f"Fields updated: {', '.join(updated_fields)}"
            )

        return instance

    def validate(self, data):
        availability = data.get('availability')
        request = self.context.get('request')
        patient = request.user if request else None

        # Only validate availability if it's being updated
        if availability:
            # CRITICAL BUG FIX: Check for existing appointment first (prevents OneToOneField violation)
            if hasattr(availability, 'appointment'):
                raise serializers.ValidationError("This appointment slot is already taken.")
                
            if availability.is_booked:
                raise serializers.ValidationError("This slot is already booked.")

            new_start = availability.start_time
            new_end = availability.end_time

            overlapping = Appointment.objects.filter(
                patient=patient,
                availability__start_time__lt=new_end,
                availability__end_time__gt=new_start,
            ).exclude(
                pk=self.instance.pk if self.instance else None
            ).exclude(status__in=['cancelled_by_patient', 'cancelled_by_doctor', 'cancelled_by_admin'])

            if overlapping.exists():
                raise serializers.ValidationError("You already have an appointment during this time.")

        return data

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
