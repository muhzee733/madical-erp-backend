from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from .models import AppointmentAvailability
from users.permissions import IsDoctor,IsPatient

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDoctor])
def post_schedule(request):
    data_list = request.data

    if not isinstance(data_list, list):
        return Response({"error": "Payload should be a list of appointments."}, status=status.HTTP_400_BAD_REQUEST)

    if not data_list:
        return Response({"error": "Appointment list is empty."}, status=status.HTTP_400_BAD_REQUEST)

    first_date = data_list[0].get('date')  # Sare times ek hi date pe honge

    if not first_date:
        return Response({"error": "Each appointment must have 'date'."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate future date
    if datetime.strptime(first_date, "%Y-%m-%d").date() < datetime.now().date():
        return Response({"error": f"Date {first_date} must be in the future."}, status=status.HTTP_400_BAD_REQUEST)

    # --- Collect all start times ---
    start_times = []
    for item in data_list:
        start_time = item.get('start_time')
        if not start_time:
            return Response({"error": "Each appointment must have 'start_time'."}, status=status.HTTP_400_BAD_REQUEST)

        if len(start_time.split(":")) == 2:
            start_time += ":00"

        try:
            start_time_obj = datetime.strptime(start_time, "%H:%M:%S").time()
        except ValueError:
            return Response({"error": "start_time format should be HH:MM or HH:MM:SS"}, status=status.HTTP_400_BAD_REQUEST)

        start_times.append(start_time_obj)

    # --- Check if any of the start_times already exist for that date ---
    existing_slots = AppointmentAvailability.objects.filter(
        doctor=request.user,
        date=first_date,
        start_time__in=start_times
    )

    if existing_slots.exists():
        existing_times = [slot.start_time.strftime("%H:%M:%S") for slot in existing_slots]
        return Response({
            "created": "false",
            "message": f"Some time slots on {first_date} are already scheduled. {existing_times}",
        }, status=status.HTTP_200_OK)

    # --- If all clear, create appointments ---
    created_appointments = []
    for start_time in start_times:
        end_time_obj = (datetime.combine(datetime.today(), start_time) + timedelta(minutes=15)).time()

        appointment = AppointmentAvailability.objects.create(
            doctor=request.user,
            date=first_date,
            start_time=start_time,
            end_time=end_time_obj
        )
        created_appointments.append({
            "id": appointment.id,
            "date": appointment.date,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
        })

    return Response({
        "created": True,
        "message": f"{len(created_appointments)} appointments added successfully.",
        "appointments": created_appointments
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDoctor])
def get_doctor_appointments(request):
    doctor_id = request.user.id
    appointments = AppointmentAvailability.objects.filter(doctor_id=doctor_id).order_by('date', 'start_time')
    appointment_list = []
    for appointment in appointments:
        appointment_list.append({
            "id": appointment.id,
            "date": appointment.date,
            "start_time": appointment.start_time.strftime("%H:%M:%S"),
            "end_time": appointment.end_time.strftime("%H:%M:%S"),
        })
    return Response({
        "success": "true",
        "appointments": appointment_list
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsPatient])
def get_all_appointments(request):
    appointments = AppointmentAvailability.objects.all().select_related('doctor').order_by('doctor', 'date', 'start_time')
    
    doctor_appointments = {}

    # Group appointments by doctor
    for appointment in appointments:
        doctor = appointment.doctor

        # If doctor is not already in the dictionary, add them
        if doctor.id not in doctor_appointments:
            doctor_appointments[doctor.id] = {
                "id": doctor.id,
                "email": doctor.email,
                "first_name": doctor.first_name,
                "last_name": doctor.last_name,
                "appointments": []
            }

        # Add appointment to the doctor's list of appointments
        doctor_appointments[doctor.id]["appointments"].append({
            "id": appointment.id,
            "date": appointment.date,
            "is_booked": appointment.is_booked,
            "start_time": appointment.start_time.strftime("%H:%M:%S"),
            "end_time": appointment.end_time.strftime("%H:%M:%S"),
        })
    
    # Convert the dictionary to a list of doctor data
    doctors_data = list(doctor_appointments.values())

    return Response({
        "success": "true",
        "doctors": doctors_data
    }, status=status.HTTP_200_OK)


