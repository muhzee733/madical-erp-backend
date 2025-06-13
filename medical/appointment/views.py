from rest_framework import generics, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.utils.timezone import make_aware
import pytz
from rest_framework.pagination import PageNumberPagination

from users.serializers import DoctorProfileSerializer, PatientProfileSerializer, UserSerializer
from .models import AppointmentAvailability, Appointment, AppointmentActionLog
from .serializers import (
    AppointmentAvailabilitySerializer,
    AppointmentSerializer,
    AppointmentActionLogSerializer
)
from users.permissions import IsDoctor,IsPatient
from notifications.utils import send_appointment_confirmation

class MyAvailabilityPagination(PageNumberPagination):
    page_size = 10  # default page size
    page_size_query_param = 'page_size'
    max_page_size = 100

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
    
class CustomAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    SLOT_DURATIONS = {
        "short": 15,
        "long": 30,
    }

    def post(self, request):
        user = request.user
        date = request.data.get("date")
        start_times = request.data.get("start_times", [])
        slot_type = request.data.get("slot_type", "short")
        timezone_str = "Australia/Brisbane"

        if not date or not start_times:
            return Response({"error": "Both 'date' and 'start_times' are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if slot_type not in self.SLOT_DURATIONS:
            return Response({"error": "Invalid slot_type. Choose 'short' or 'long'."},
                            status=status.HTTP_400_BAD_REQUEST)

        duration_minutes = self.SLOT_DURATIONS[slot_type]
        tz = ZoneInfo(timezone_str)

        new_slots = []
        for time_str in start_times:
            try:
                start_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                start_dt = make_aware(start_dt.replace(tzinfo=None), timezone=tz)
                end_dt = start_dt + timedelta(minutes=duration_minutes)
            except ValueError:
                return Response({"error": f"Invalid time format: {time_str}"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Check for overlap with existing availabilities
            if AppointmentAvailability.objects.filter(
                doctor=user,
                start_time__lt=end_dt,
                end_time__gt=start_dt
            ).exists():
                return Response({"error": f"Time slot {time_str} on {date} overlaps with existing availability."},
                                status=status.HTTP_400_BAD_REQUEST)

            new_slots.append(AppointmentAvailability(
                doctor=user,
                start_time=start_dt,
                end_time=end_dt,
                slot_type=slot_type,
                timezone=timezone_str,
            ))

        # Check for overlap among the submitted times themselves
        sorted_slots = sorted(new_slots, key=lambda x: x.start_time)
        for i in range(len(sorted_slots) - 1):
            if sorted_slots[i].end_time > sorted_slots[i + 1].start_time:
                return Response({"error": "Some start_times in the list overlap with each other."},
                                status=status.HTTP_400_BAD_REQUEST)

        AppointmentAvailability.objects.bulk_create(new_slots)

        serialized_slots = AppointmentAvailabilitySerializer(new_slots, many=True)
        return Response({"message": "Custom availability slots created successfully.", "slots": serialized_slots.data},
                        status=status.HTTP_201_CREATED)

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
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MyAvailabilityPagination  # Enable page & page_size query params

    def get_queryset(self):
        user = self.request.user
        queryset = AppointmentAvailability.objects.all().order_by("id")
        if user.role == 'doctor':
            queryset = queryset.filter(doctor=user)
        elif user.role == 'patient':
            doctor_id = self.request.query_params.get('doctor')
            if doctor_id:
                queryset = queryset.filter(doctor__id=doctor_id)
        else:
            return AppointmentAvailability.objects.none()

        # New query params
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        is_booked = self.request.query_params.get('is_booked')

        if start_time:
            queryset = queryset.filter(start_time__gte=start_time)
        if end_time:
            queryset = queryset.filter(end_time__lte=end_time)
        if is_booked is not None:
            if is_booked.lower() == 'true':
                queryset = queryset.filter(is_booked=True)
            elif is_booked.lower() == 'false':
                queryset = queryset.filter(is_booked=False)

        return queryset

class ListAvailableAppointmentsView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            return Appointment.objects.none()
        return Appointment.objects.all().order_by("availability__start_time")


class BookAppointmentView(generics.CreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def create(self, request, *args, **kwargs):
        # Run the serializer and perform_create logic
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return full serialized appointment including `id`
        return Response(self.get_serializer(self.appointment).data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        availability = serializer.validated_data['availability']
        availability.is_booked = True
        availability.save()

        # Save appointment with status 'pending'
        self.appointment = serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            is_deleted=False,
            status='pending',  # Set status to 'pending' when booking
        )

        # Log appointment creation
        AppointmentActionLog.objects.create(
            appointment=self.appointment,
            action_type="created",
            performed_by=self.request.user
        )

        # Auto-send appointment confirmation
        patient = self.appointment.patient
        start_time = self.appointment.availability.start_time.strftime('%A, %d %B %Y at %I:%M %p')
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
            related_id=self.appointment.id
        )

        # Schedule Celery task to expire appointment in 15 minutes
        from .tasks import expire_pending_appointment
        expire_pending_appointment.apply_async(args=[self.appointment.id], countdown=15*60)

class UpdateAppointmentView(generics.UpdateAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            return Appointment.objects.filter(patient=user, is_deleted=False)
        elif user.role == 'doctor':
            return Appointment.objects.filter(availability__doctor=user, is_deleted=False)
        elif user.role == 'admin':
            return Appointment.objects.filter(is_deleted=False)
        return Appointment.objects.none()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class CancelAppointmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, appointment_id):
        user = request.user

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

class AppointmentPartyInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, appointment_id):
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found."}, status=404)

        if appointment.availability.doctor != request.user:
            return Response({"error": "You are not authorized to access this appointment."}, status=403)

        patient_user = appointment.patient
        doctor_user = appointment.availability.doctor

        patient_profile = getattr(patient_user, 'patientprofile', None)
        doctor_profile = getattr(doctor_user, 'doctorprofile', None)

        if not patient_profile or not doctor_profile:
            return Response({"error": "Profile information is missing."}, status=400)

        data = {
            "patient_user": UserSerializer(patient_user).data,
            "patient_profile": PatientProfileSerializer(patient_profile).data,
            "doctor_user": UserSerializer(doctor_user).data,
            "doctor_profile": DoctorProfileSerializer(doctor_profile).data,
        }

        return Response(data, status=200)
