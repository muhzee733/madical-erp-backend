from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from .models import AppointmentAvailability
from users.permissions import IsDoctor,IsPatient
from order.models import Order

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointment_details(request, appointment_id):
    try:
        print(f"Looking for ID: {appointment_id}")
        
        # First try to get the appointment directly
        try:
            appointment = AppointmentAvailability.objects.select_related('doctor').get(id=appointment_id)
            print("Found appointment directly")
        except AppointmentAvailability.DoesNotExist:
            print("Not found as appointment, checking if it's an order ID...")
            # If not found as appointment, try to get it through orders
            try:
                # Try to find order with this ID
                order = Order.objects.select_related('appointment', 'appointment__doctor').get(id=appointment_id)
                appointment = order.appointment
                print(f"Found appointment through order ID: {order.id}")
            except Order.DoesNotExist:
                print("Not found as order ID, checking orders with this appointment ID...")
                # If not found as order ID, try to find orders with this appointment ID
                orders = Order.objects.filter(appointment_id=appointment_id)
                if orders.exists():
                    order = orders.first()
                    appointment = order.appointment
                    print(f"Found appointment through appointment ID in orders")
                else:
                    return Response({
                        "error": "No appointment or order found with this ID"
                    }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the user is either the doctor or a patient
        if request.user != appointment.doctor and not hasattr(request.user, 'is_patient'):
            return Response({
                "error": "You don't have permission to view this appointment"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get order information if it exists
        order = None
        try:
            order = Order.objects.get(appointment=appointment)
            print(f"Found associated order: {order.id}")
        except Order.DoesNotExist:
            print("No associated order found")
            pass
        
        appointment_data = {
            "id": appointment.id,
            "date": appointment.date,
            "start_time": appointment.start_time.strftime("%H:%M:%S"),
            "end_time": appointment.end_time.strftime("%H:%M:%S"),
            "is_booked": appointment.is_booked,
            "price": str(appointment.price),
            "created_at": appointment.created_at,
            "doctor": {
                "id": appointment.doctor.id,
                "email": appointment.doctor.email,
                "first_name": appointment.doctor.first_name,
                "last_name": appointment.doctor.last_name
            },
            "order": {
                "id": str(order.id) if order else None,
                "status": order.status if order else None,
                "amount": str(order.amount) if order else None,
                "created_at": order.created_at if order else None,
                "payment_intent": order.payment_intent if order else None,
                "stripe_session_id": order.stripe_session_id if order else None
            } if order else None
        }
        
        return Response({
            "success": True,
            "appointment": appointment_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_appointment_details: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


