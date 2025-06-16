from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from appointment.models import Appointment, AppointmentAvailability
from .models import Order
from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import now

class OrderFlowTests(APITestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(email='doc@example.com', password='testpass', role='doctor')
        self.patient = User.objects.create_user(email='pat@example.com', password='testpass', role='patient')
        future_start = now() + timedelta(days=1)
        future_end = future_start + timedelta(minutes=15)
        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=future_start,
            end_time=future_end,
            slot_type='short',
            timezone='Australia/Brisbane',
            is_booked=False
        )
        self.appointment = Appointment.objects.create(
            availability=self.availability,
            patient=self.patient,
            status='booked',
            price=80.00
        )
        self.client.force_authenticate(user=self.patient)

    def test_create_order_for_appointment(self):
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.appointment, self.appointment)
        self.assertEqual(order.amount, self.appointment.price)
        self.assertEqual(order.user, self.patient)

    def test_cannot_create_duplicate_order(self):
        Order.objects.create(user=self.patient, appointment=self.appointment, amount=80.00)
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('already booked', response.data['message'])

    def test_order_list_patient(self):
        Order.objects.create(user=self.patient, appointment=self.appointment, amount=80.00)
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['appointment']['id'], str(self.appointment.id))

    def test_order_list_doctor(self):
        Order.objects.create(user=self.patient, appointment=self.appointment, amount=80.00)
        self.client.force_authenticate(user=self.doctor)
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['appointment']['id'], str(self.appointment.id))

class OrderEdgeCaseTests(APITestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(email='doc@example.com', password='testpass', role='doctor')
        self.patient = User.objects.create_user(email='pat@example.com', password='testpass', role='patient')
        self.other_patient = User.objects.create_user(email='other@example.com', password='testpass', role='patient')
        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, minutes=15),
            slot_type='short',
            timezone='Australia/Brisbane',
            is_booked=False
        )
        self.appointment = Appointment.objects.create(
            availability=self.availability,
            patient=self.patient,
            status='booked',
            price=80.00
        )
        self.client.force_authenticate(user=self.patient)

    def test_cannot_order_for_cancelled_appointment(self):
        self.appointment.status = 'cancelled_by_patient'
        self.appointment.save()
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_order_for_completed_appointment(self):
        self.appointment.status = 'completed'
        self.appointment.save()
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_order_for_past_appointment(self):
        self.availability.start_time = timezone.now() - timedelta(days=1)
        self.availability.end_time = timezone.now() - timedelta(days=1, minutes=-15)
        self.availability.save()
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_order_for_other_patients_appointment(self):
        self.client.force_authenticate(user=self.other_patient)
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_user_cannot_create_order(self):
        self.client.logout()
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_create_second_order_for_same_appointment(self):
        Order.objects.create(user=self.patient, appointment=self.appointment, amount=80.00)
        url = reverse('create-order')
        response = self.client.post(url, {'appointmentId': str(self.appointment.id)}, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)
