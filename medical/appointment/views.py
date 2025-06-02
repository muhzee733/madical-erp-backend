from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
import pytz
from .models import AppointmentAvailability, Appointment, AppointmentActionLog
from .serializers import (
    AppointmentAvailabilitySerializer,
    AppointmentSerializer,
    AppointmentActionLogSerializer
)
from users.permissions import IsDoctor,IsPatient
from notifications.utils import send_appointment_confirmation

class CreateAvailabilityView(generics.CreateAPIView):
    serializer_class = AppointmentAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)


class BulkAvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request):
        user = request.user
        data = request.data

        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        days_of_week = data['days_of_week']
        start_time_str = data['start_time']
        end_time_str = data['end_time']
        slot_type = data['slot_type']
        timezone_str = data['timezone']

        tz = pytz.timezone(timezone_str)
        created_slots = []
        interval = timedelta(minutes=15 if slot_type == 'short' else 30)

        current_date = start_date
        while current_date <= end_date:
            if current_date.strftime('%A') in days_of_week:
                start_dt = tz.localize(datetime.combine(current_date, datetime.strptime(start_time_str, '%H:%M').time()))
                end_dt = tz.localize(datetime.combine(current_date, datetime.strptime(end_time_str, '%H:%M').time()))

                slot_start = start_dt
                while slot_start + interval <= end_dt:
                    slot_end = slot_start + interval
                    if not AppointmentAvailability.objects.filter(
                        doctor=user,
                        start_time=slot_start
                    ).exists():
                        created_slots.append(AppointmentAvailability(
                            doctor=user,
                            start_time=slot_start,
                            end_time=slot_end,
                            slot_type=slot_type,
                            timezone=timezone_str
                        ))
                    slot_start = slot_end
            current_date += timedelta(days=1)

        AppointmentAvailability.objects.bulk_create(created_slots)
        return Response({"message": f"{len(created_slots)} slots created."}, status=201)
    

class EditAvailabilityView(generics.UpdateAPIView):
    queryset = AppointmentAvailability.objects.all().order_by("id")
    serializer_class = AppointmentAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.is_booked:
            raise serializers.ValidationError("Cannot edit a booked slot.")
        serializer.save()


class DeleteAvailabilityView(generics.DestroyAPIView):
    queryset = AppointmentAvailability.objects.all().order_by("id")
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def perform_destroy(self, instance):
        if instance.is_booked:
            raise serializers.ValidationError("Cannot delete a booked slot.")
        instance.delete()


class MarkAppointmentCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        user = request.user

        if user.role == 'doctor':
            appointment = get_object_or_404(Appointment, id=appointment_id, availability__doctor=user)
        elif user.role == 'admin':
            appointment = get_object_or_404(Appointment, id=appointment_id)
        else:
            return Response({"error": "Unauthorized role."}, status=403)

        appointment.status = 'completed'
        appointment.save()

        AppointmentActionLog.objects.create(
            appointment=appointment,
            action_type="completed",
            performed_by=user
        )
        return Response({"message": f"Appointment marked as completed by {user.role}."})



class MarkAppointmentNoShowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        user = request.user

        if user.role == 'doctor':
            appointment = get_object_or_404(Appointment, id=appointment_id, availability__doctor=user)
        elif user.role == 'admin':
            appointment = get_object_or_404(Appointment, id=appointment_id)
        else:
            return Response({"error": "Unauthorized role."}, status=403)

        appointment.status = 'no_show'
        appointment.save()

        AppointmentActionLog.objects.create(
            appointment=appointment,
            action_type="no_show",
            performed_by=user
        )
        return Response({"message": f"Appointment marked as no-show by {user.role}."})


class ListMyAvailabilityView(generics.ListAPIView):
    serializer_class = AppointmentAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get_queryset(self):
        return AppointmentAvailability.objects.filter(doctor=self.request.user).order_by("id")


class ListAvailableAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_queryset(self):
        queryset = AppointmentAvailability.objects.filter(is_booked=False, start_time__gte=now()).order_by("id")

        doctor_name = self.request.query_params.get("doctor_name")
        specialty = self.request.query_params.get("specialty")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        slot_type = self.request.query_params.get("slot_type")

        if doctor_name:
            queryset = queryset.filter(doctor__first_name__icontains=doctor_name)
        if specialty:
            queryset = queryset.filter(doctor__doctorprofile__specialty__icontains=specialty)
        if date_from:
            queryset = queryset.filter(start_time__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_time__date__lte=date_to)
        if slot_type:
            queryset = queryset.filter(slot_type=slot_type)

        return queryset


class BookAppointmentView(generics.CreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def perform_create(self, serializer):
        availability = serializer.validated_data['availability']
        availability.is_booked = True
        availability.save()

        appointment = serializer.save(
            patient=self.request.user,
            created_by=self.request.user,
            is_deleted=False
        )

        # Log appointment creation
        AppointmentActionLog.objects.create(
            appointment=appointment,
            action_type="created",
            performed_by=self.request.user
        )

        # Auto-send appointment confirmation
        patient = appointment.patient
        start_time = appointment.availability.start_time.strftime('%A, %d %B %Y at %I:%M %p')
        subject = "Appointment Confirmation"
        body = (
            f"Dear {patient.get_full_name()},\n\n"
            f"Your appointment has been successfully booked for {start_time}.\n\n"
            "Regards,\nProMedicine Team"
        )

        send_appointment_confirmation(
            to_email=patient.email,
            subject=subject,
            body=body,
            related_id=appointment.id
        )

class CancelAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        user = request.user

        # Determine which role is cancelling
        if user.role == 'patient':
            appointment = get_object_or_404(Appointment, id=appointment_id, patient=user)
            # Enforce 1-hour cancellation window for patients only
            minutes_left = (appointment.availability.start_time - now()).total_seconds() / 60
            if minutes_left < 60:
                return Response({"error": "Cannot cancel less than 1 hour before appointment."}, status=400)
            cancel_status = 'cancelled_by_patient'

        elif user.role == 'doctor':
            appointment = get_object_or_404(Appointment, id=appointment_id, availability__doctor=user)
            cancel_status = 'cancelled_by_doctor'

        elif user.role == 'admin':
            appointment = get_object_or_404(Appointment, id=appointment_id)
            cancel_status = 'cancelled_by_admin'

        else:
            return Response({"error": "Unauthorized role."}, status=403)

        # Cancel the appointment
        appointment.status = cancel_status
        appointment.updated_by = user        
        appointment.save()

        # Free the availability slot
        availability = appointment.availability
        availability.is_booked = False
        availability.save()

        # Log the cancellation
        AppointmentActionLog.objects.create(
            appointment=appointment,
            action_type="cancelled",
            performed_by=user
        )

        return Response({"message": f"Appointment cancelled by {user.role}."}, status=200)


class RescheduleAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        user = request.user
        new_availability_id = request.data.get('new_availability_id')

        if not new_availability_id:
            return Response({"error": "New availability ID is required."}, status=400)

        # Identify and authorize the old appointment
        if user.role == 'patient':
            old_appointment = get_object_or_404(Appointment, id=appointment_id, patient=user)
        elif user.role == 'doctor':
            old_appointment = get_object_or_404(Appointment, id=appointment_id, availability__doctor=user)
        elif user.role == 'admin':
            old_appointment = get_object_or_404(Appointment, id=appointment_id)
        else:
            return Response({"error": "Unauthorized role."}, status=403)

        # Fetch the new availability
        new_availability = get_object_or_404(AppointmentAvailability, id=new_availability_id, is_booked=False)

        # Mark old as rescheduled
        old_appointment.status = 'rescheduled'
        old_appointment.updated_by = user
        old_appointment.save()

        old_appointment.availability.is_booked = False
        old_appointment.availability.save()

        # Create the new appointment
        new_appointment = Appointment.objects.create(
            availability=new_availability,
            patient=old_appointment.patient,
            status='booked',
            rescheduled_from=old_appointment,
            created_by=user,
            is_deleted=False
        )
        new_availability.is_booked = True
        new_availability.save()

        # Log the action
        AppointmentActionLog.objects.create(
            appointment=new_appointment,
            action_type="rescheduled",
            performed_by=user
        )

        return Response({"message": f"Appointment rescheduled by {user.role}."}, status=200)

class ListMyAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'doctor':
            return Appointment.objects.filter(availability__doctor=user, is_deleted=False).order_by("id")
        return Appointment.objects.filter(patient=user).order_by("id")


class AppointmentLogView(generics.ListAPIView):
    serializer_class = AppointmentActionLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        get_object_or_404(Appointment, id=self.kwargs['appointment_id'])
        return AppointmentActionLog.objects.filter(appointment_id=self.kwargs['appointment_id']).order_by("id")

class AppointmentDetailView(generics.RetrieveAPIView):
    queryset = Appointment.objects.select_related('patient', 'availability')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
