from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from users.models import User
from appointment.models import AppointmentAvailability
from prescriptions.models import Drug
from django.utils import timezone
import uuid

class NotificationAutoSendTests(APITestCase):

    def setUp(self):
        self.doctor = User.objects.create_user(
            email="doc@example.com", password="doc123", role="doctor"
        )
        self.patient = User.objects.create_user(
            email="pat@example.com", password="pat123", role="patient"
        )
        self.client.force_authenticate(user=self.patient)

    @patch("appointment.views.send_appointment_confirmation")
    def test_email_sent_when_appointment_created(self, mock_send):
        # First create an availability slot (simulates doctor setup)
        availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, minutes=15),
            is_booked=False
        )

        # Book an appointment (this should auto-trigger an email)
        response = self.client.post(reverse("book-appointment"), {
            "availability": str(availability.id),
            "reason": "Checkup"
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send.assert_called_once()

