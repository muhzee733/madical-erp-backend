from types import SimpleNamespace
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse, resolve
from unittest.mock import patch
from django.utils import timezone
from users.models import User

class NotificationEmailTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="doctor@example.com", password="password123", role="doctor"
        )
        self.client.force_authenticate(user=self.user)
        self.appointment_url = reverse("resend-appointment-confirmation")
        self.prescription_url = reverse("send-prescription-email")


    # --- Success cases with mocks ---

    @patch("notifications.views.send_appointment_confirmation")
    @patch("notifications.views.get_object_or_404")
    def test_resend_appointment_email_success(self, mock_get, mock_send):
        fake_appt = SimpleNamespace(
            id=1,
            patient=SimpleNamespace(
                email="patient@example.com",
                get_full_name=lambda: "Test Patient",
            ),
            availability=SimpleNamespace(
                start_time=timezone.now(),
            ),
        )
        mock_get.return_value = fake_appt

        payload = {"email": "patient@example.com", "appointment_id": 1}
        response = self.client.post(self.appointment_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Appointment confirmation email sent.")
        mock_send.assert_called_once()

    @patch("notifications.views.send_prescription_email")
    @patch("notifications.views.get_object_or_404")
    def test_send_prescription_email_success(self, mock_get, mock_send):
        fake_rx = SimpleNamespace(
            id=1,
            patient=SimpleNamespace(
                email="pharmacy@example.com",
                get_full_name=lambda: "Test Patient",
            ),
        )
        mock_get.return_value = fake_rx

        payload = {"email": "pharmacy@example.com", "prescription_id": 1}
        response = self.client.post(self.prescription_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Prescription email sent.")
        mock_send.assert_called_once()

    # --- Validation & auth errors ---

    def test_resend_appointment_email_missing_email(self):
        response = self.client.post(self.appointment_url, {"appointment_id": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_send_prescription_email_missing_email(self):
        response = self.client.post(self.prescription_url, {"prescription_id": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_resend_appointment_missing_id(self):
        response = self.client.post(self.appointment_url, {"email": "patient@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_prescription_missing_id(self):
        response = self.client.post(self.prescription_url, {"email": "pharmacy@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access_blocked(self):
        self.client.force_authenticate(user=None)  # logout
        response = self.client.post(self.appointment_url, {
            "email": "patient@example.com",
            "appointment_id": 1
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Sanity check ---

    def test_url_resolves_to_correct_view(self):
        match = resolve("/api/v1/notifications/appointment/confirm/")
        self.assertEqual(match.view_name, "resend-appointment-confirmation")
