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


class BillingIntegrationTests(APITestCase):
    """Test billing logic integration with appointment pricing"""
    
    def setUp(self):
        self.client.logout()  # Ensure clean state
        
        # Create test users
        self.doctor = User.objects.create_user(
            email='doctor@billing.com',
            password='testpass',
            role='doctor',
            first_name='Dr. Test',
            last_name='Doctor'
        )
        
        self.new_patient = User.objects.create_user(
            email='newpatient@billing.com',
            password='testpass',
            role='patient',
            first_name='New',
            last_name='Patient'
        )
        
        self.returning_patient = User.objects.create_user(
            email='returning@billing.com',
            password='testpass',
            role='patient',
            first_name='Returning',
            last_name='Patient'
        )
        
        # Create required profiles
        from users.models import DoctorProfile, PatientProfile
        DoctorProfile.objects.create(
            user=self.doctor,
            gender='male',
            date_of_birth='1980-01-01',
            qualification='MBBS',
            specialty='General Practice',
            medical_registration_number='DOC123',
            prescriber_number='PRES123',
            provider_number='PROV123'
        )
        
        PatientProfile.objects.create(
            user=self.new_patient,
            gender='male',
            date_of_birth='1990-01-01',
            contact_address='123 New St'
        )
        
        PatientProfile.objects.create(
            user=self.returning_patient,
            gender='female',
            date_of_birth='1985-01-01',
            contact_address='456 Return Ave'
        )
        
        # Create availability slots
        future_time = timezone.now() + timedelta(days=1)
        self.availability1 = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=future_time,
            end_time=future_time + timedelta(minutes=30),
            slot_type='short',
            timezone='UTC',
            is_booked=False
        )
        
        self.availability2 = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=future_time + timedelta(hours=1),
            end_time=future_time + timedelta(hours=1, minutes=30),
            slot_type='short',
            timezone='UTC',
            is_booked=False
        )
        
        # Create a completed appointment for returning patient to establish history
        past_availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=timezone.now() - timedelta(days=30),
            end_time=timezone.now() - timedelta(days=30, minutes=-30),
            slot_type='short',
            timezone='UTC',
            is_booked=True
        )
        
        past_appointment = Appointment.objects.create(
            availability=past_availability,
            patient=self.returning_patient,
            status='completed',  # This establishes the patient as returning
            price=80.00,
            is_initial=True
        )
    
    def test_new_patient_pricing(self):
        """Test that new patients are charged $80 (NEW_PATIENT_FEE)"""
        from appointment.constants import NEW_PATIENT_FEE
        
        # New patient books appointment
        self.client.force_authenticate(user=self.new_patient)
        response = self.client.post('/api/v1/appointments/', {
            'availability_id': self.availability1.id
        })
        
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(id=response.data['id'])
        
        # Verify pricing
        self.assertEqual(appointment.price, NEW_PATIENT_FEE)
        self.assertTrue(appointment.is_initial)
        
        # Test order creation with correct pricing
        order_response = self.client.post(reverse('create-order'), {
            'appointmentId': str(appointment.id)
        })
        
        if order_response.status_code == 201:
            order = Order.objects.get(appointment=appointment)
            self.assertEqual(order.amount, NEW_PATIENT_FEE)
    
    def test_returning_patient_pricing(self):
        """Test that returning patients are charged $50 (RETURNING_PATIENT_FEE)"""
        from appointment.constants import RETURNING_PATIENT_FEE
        
        # Returning patient books new appointment
        self.client.force_authenticate(user=self.returning_patient)
        response = self.client.post('/api/v1/appointments/', {
            'availability_id': self.availability2.id
        })
        
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(id=response.data['id'])
        
        # Verify pricing
        self.assertEqual(appointment.price, RETURNING_PATIENT_FEE)
        self.assertFalse(appointment.is_initial)
        
        # Test order creation with correct pricing
        order_response = self.client.post(reverse('create-order'), {
            'appointmentId': str(appointment.id)
        })
        
        if order_response.status_code == 201:
            order = Order.objects.get(appointment=appointment)
            self.assertEqual(order.amount, RETURNING_PATIENT_FEE)
    
    def test_pricing_sequence_flow(self):
        """Test complete flow: new patient ($80) then returning patient ($50)"""
        from appointment.constants import NEW_PATIENT_FEE, RETURNING_PATIENT_FEE
        
        # Step 1: Patient books first appointment (should be $80)
        self.client.force_authenticate(user=self.new_patient)
        first_response = self.client.post('/api/v1/appointments/', {
            'availability_id': self.availability1.id
        })
        
        self.assertEqual(first_response.status_code, 201)
        first_appointment = Appointment.objects.get(id=first_response.data['id'])
        self.assertEqual(first_appointment.price, NEW_PATIENT_FEE)
        self.assertTrue(first_appointment.is_initial)
        
        # Step 2: Mark first appointment as completed
        first_appointment.status = 'completed'
        first_appointment.save()
        
        # Step 3: Same patient books second appointment (should be $50)
        second_response = self.client.post('/api/v1/appointments/', {
            'availability_id': self.availability2.id
        })
        
        self.assertEqual(second_response.status_code, 201)
        second_appointment = Appointment.objects.get(id=second_response.data['id'])
        self.assertEqual(second_appointment.price, RETURNING_PATIENT_FEE)
        self.assertFalse(second_appointment.is_initial)
    
    def test_pricing_consistency_across_different_doctors(self):
        """Test that returning patient rates apply even with different doctors"""
        from appointment.constants import RETURNING_PATIENT_FEE
        
        # Create another doctor
        doctor2 = User.objects.create_user(
            email='doctor2@billing.com',
            password='testpass',
            role='doctor'
        )
        
        from users.models import DoctorProfile
        DoctorProfile.objects.create(
            user=doctor2,
            gender='female',
            date_of_birth='1975-01-01',
            qualification='MBBS',
            specialty='Cardiology',
            medical_registration_number='DOC456',
            prescriber_number='PRES456',
            provider_number='PROV456'
        )
        
        # Create availability with different doctor
        availability_doc2 = AppointmentAvailability.objects.create(
            doctor=doctor2,
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, minutes=30),
            slot_type='short',
            timezone='UTC',
            is_booked=False
        )
        
        # Returning patient books with different doctor
        self.client.force_authenticate(user=self.returning_patient)
        response = self.client.post('/api/v1/appointments/', {
            'availability_id': availability_doc2.id
        })
        
        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get(id=response.data['id'])
        
        # Should still get returning patient rate even with different doctor
        self.assertEqual(appointment.price, RETURNING_PATIENT_FEE)
        self.assertFalse(appointment.is_initial)
