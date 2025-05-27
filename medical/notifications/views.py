from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from .utils import send_appointment_confirmation, send_prescription_email
from appointment.models import Appointment
from prescriptions.models import Prescription

class ResendAppointmentConfirmationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        email = request.data.get("email")
        appointment_id = request.data.get("appointment_id")

        if not email or not appointment_id:
            return Response({"error": "Email and appointment_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate appointment
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.patient.email != email:
            return Response({"error": "Email does not match patient for this appointment."}, status=status.HTTP_400_BAD_REQUEST)

        message = f"Hi {appointment.patient.get_full_name()}, your appointment on {appointment.availability.start_time.strftime('%Y-%m-%d %H:%M')} is confirmed."
        send_appointment_confirmation(email, "Appointment Confirmation", message)

        return Response({"success": True, "message": "Appointment confirmation email sent."}, status=status.HTTP_200_OK)


class SendPrescriptionEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        email = request.data.get("email")
        prescription_id = request.data.get("prescription_id")

        if not email or not prescription_id:
            return Response({"error": "Email and prescription_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate prescription
        prescription = get_object_or_404(Prescription, id=prescription_id)
        if prescription.patient.email != email:
            return Response({"error": "Email does not match patient for this prescription."}, status=status.HTTP_400_BAD_REQUEST)

        download_link = f"https://yourdomain.com/api/v1/prescriptions/pdf/{prescription.id}/"
        message = f"Hi {prescription.patient.get_full_name()}, your prescription is ready. Download it here: {download_link}"

        send_prescription_email(email, "Prescription Ready", message)

        return Response({"success": True, "message": "Prescription email sent."}, status=status.HTTP_200_OK)
