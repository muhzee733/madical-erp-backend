from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User, DoctorProfile, PatientProfile
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


class UserViewTests(APITestCase):

    def setUp(self):
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        
        # Create an admin, doctor, and patient user
        self.admin_user = User.objects.create_user(
            email="admin@example.com", password="admin123", role="admin"
        )
        self.doctor_user = User.objects.create_user(
            email="doctor@example.com", password="doctor123", role="doctor"
        )
        self.patient_user = User.objects.create_user(
            email="patient@example.com", password="patient123", role="patient"
        )

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_user_registration(self):
        data = {
            "email": "newuser@example.com",
            "password": "newuser123",
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "0400000000",
            "role": "doctor"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Duplicate registration
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            "email": "doctor@example.com",
            "password": "doctor123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_success_and_failure(self):
        success = self.client.post(self.login_url, {"email": "doctor@example.com", "password": "doctor123"})
        self.assertEqual(success.status_code, status.HTTP_200_OK)
        self.assertIn("access", success.data)

        fail = self.client.post(self.login_url, {"email": "doctor@example.com", "password": "wrong"})
        self.assertEqual(fail.status_code, status.HTTP_200_OK)
        self.assertEqual(fail.data["message"], "Incorrect password")

    def test_login_invalid_password(self):
        response = self.client.post(self.login_url, {
            "email": "doctor@example.com",
            "password": "wrongpass"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Incorrect password")

    def test_dashboard_access(self):
        # Patient
        self.authenticate(self.patient_user)
        res = self.client.get(reverse("patient-dashboard"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Doctor
        self.authenticate(self.doctor_user)
        res = self.client.get(reverse("doctor-dashboard"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Admin
        self.authenticate(self.admin_user)
        res = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Unauthenticated
        self.client.credentials()
        res = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_doctor_profile_crud(self):
        self.authenticate(self.doctor_user)

        # Create doctor profile
        data = {
            "gender": "male",
            "date_of_birth": "1980-06-15",
            "qualification": "MBBS",
            "specialty": "General Practice",
            "medical_registration_number": "MED123456",
            "prescriber_number": "2345678T",
            "provider_number": "1234567A",
            "hpi_i": "8003608166690503"
        }
        res = self.client.post(reverse("doctor-profile-create"), data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Retrieve doctor profile
        res = self.client.get(reverse("doctor-profile"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["specialty"], data["specialty"])

        # Update doctor profile
        updated_data = {"specialty": "Cardiology"}
        res = self.client.patch(reverse("doctor-profile"), updated_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["specialty"], updated_data["specialty"])

    def test_patient_profile_crud(self):
        self.authenticate(self.patient_user)

        # Create patient profile
        data = {
            "gender": "female",
            "date_of_birth": "1990-02-02",
            "contact_address": "123 Main St, Sydney",
            "medicare_number": "1234567890",
            "irn": "1",
            "medicare_expiry": "2030-12-31",
            "ihi": "8003604475901234"
        }
        res = self.client.post(reverse("patient-profile-create"), data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Retrieve patient profile
        res = self.client.get(reverse("patient-profile"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["medicare_number"], data["medicare_number"])

        # Update patient profile
        updated_data = {"medicare_number": "0987654321"}
        res = self.client.patch(reverse("patient-profile"), updated_data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["medicare_number"], updated_data["medicare_number"])

    def test_doctor_profile_forbidden_for_patient(self):
        self.authenticate(self.patient_user)
        res = self.client.get(reverse("doctor-profile"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_profile_forbidden_for_doctor(self):
        self.authenticate(self.doctor_user)
        res = self.client.get(reverse("patient-profile"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_list_and_detail(self):
        self.authenticate(self.admin_user)
        res = self.client.get(reverse("admin-user-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 3)

        user_detail_url = reverse("admin-user-detail", args=[self.doctor_user.id])
        res = self.client.get(user_detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.patch(user_detail_url, {"first_name": "Updated"}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_access_admin_views(self):
        self.authenticate(self.patient_user)
        res = self.client.get(reverse("admin-user-list"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.doctor_user)
        res = self.client.get(reverse("admin-user-list"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
