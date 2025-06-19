from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import DoctorProfile, PatientProfile
from appointment.models import AppointmentAvailability, Appointment
from .models import ChatRoom, Message, MessageReadStatus
import uuid

User = get_user_model()

class ChatRoomModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Dr. Test',
            role='doctor'
        )
        
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient Test',
            role='patient'
        )
        
        # Create profiles
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            gender='male',
            date_of_birth='1980-01-01',
            qualification='MBBS',
            specialty='General Practice',
            medical_registration_number='DOC123',
            prescriber_number='PRES123',
            provider_number='PROV123'
        )
        
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            gender='female',
            date_of_birth='1990-01-01',
            contact_address='123 Test St, Test City'
        )
        
        # Create appointment availability
        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor_user,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1),
            slot_type='long',
            timezone='UTC'
        )
        
        # Create appointment
        self.appointment = Appointment.objects.create(
            patient=self.patient_user,
            availability=self.availability,
            status='booked'
        )
    
    def test_create_chatroom_success(self):
        """Test successful chatroom creation"""
        chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        self.assertEqual(chatroom.patient, self.patient_user)
        self.assertEqual(chatroom.doctor, self.doctor_user)
        self.assertEqual(chatroom.appointment, self.appointment)
        self.assertEqual(chatroom.status, 'active')
        self.assertFalse(chatroom.is_deleted)
    
    def test_chatroom_validation_invalid_patient_role(self):
        """Test chatroom validation fails with invalid patient role"""
        # Create user with wrong role
        wrong_user = User.objects.create_user(
            email='wrong@test.com',
            password='password123',
            role='admin'
        )
        
        with self.assertRaises(ValidationError) as context:
            ChatRoom.objects.create(
                patient=wrong_user,
                doctor=self.doctor_user,
                appointment=self.appointment
            )
        
        self.assertIn('Selected user is not a patient', str(context.exception))
    
    def test_chatroom_validation_invalid_doctor_role(self):
        """Test chatroom validation fails with invalid doctor role"""
        # Create user with wrong role
        wrong_user = User.objects.create_user(
            email='wrong@test.com',
            password='password123',
            role='admin'
        )
        
        with self.assertRaises(ValidationError) as context:
            ChatRoom.objects.create(
                patient=self.patient_user,
                doctor=wrong_user,
                appointment=self.appointment
            )
        
        self.assertIn('Selected user is not a doctor', str(context.exception))
    
    def test_chatroom_validation_appointment_patient_mismatch(self):
        """Test chatroom validation fails when appointment patient doesn't match"""
        # Create another patient
        other_patient = User.objects.create_user(
            email='other@test.com',
            password='password123',
            role='patient'
        )
        
        with self.assertRaises(ValidationError) as context:
            ChatRoom.objects.create(
                patient=other_patient,
                doctor=self.doctor_user,
                appointment=self.appointment
            )
        
        self.assertIn('Appointment patient does not match room patient', str(context.exception))
    
    def test_chatroom_can_send_messages(self):
        """Test can_send_messages method"""
        chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        # Active room should allow messages
        self.assertTrue(chatroom.can_send_messages())
        
        # Inactive room should not allow messages
        chatroom.status = 'inactive'
        chatroom.save()
        self.assertFalse(chatroom.can_send_messages())
        
        # Deleted room should not allow messages
        chatroom.status = 'active'
        chatroom.is_deleted = True
        chatroom.save()
        self.assertFalse(chatroom.can_send_messages())
    
    def test_chatroom_soft_delete(self):
        """Test soft delete functionality"""
        chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        chatroom.soft_delete()
        
        self.assertTrue(chatroom.is_deleted)
        self.assertIsNotNone(chatroom.deleted_at)
        self.assertEqual(chatroom.status, 'archived')
    
    def test_chatroom_archive(self):
        """Test archive functionality"""
        chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        chatroom.archive()
        self.assertEqual(chatroom.status, 'archived')
    
    def test_chatroom_deactivate(self):
        """Test deactivate functionality"""
        chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        chatroom.deactivate()
        self.assertEqual(chatroom.status, 'inactive')


class MessageModelTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Dr. Test',
            role='doctor'
        )
        
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient Test',  
            role='patient'
        )
        
        # Create profiles
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            gender='male',
            date_of_birth='1980-01-01',
            qualification='MBBS',
            specialty='General Practice',
            medical_registration_number='DOC123',
            prescriber_number='PRES123',
            provider_number='PROV123'
        )
        
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            gender='female',
            date_of_birth='1990-01-01',
            contact_address='123 Test St, Test City'
        )
        
        # Create appointment availability
        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor_user,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1),
            slot_type='long',
            timezone='UTC'
        )
        
        # Create appointment
        self.appointment = Appointment.objects.create(
            patient=self.patient_user,
            availability=self.availability,
            status='booked'
        )
        
        # Create chatroom
        self.chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
    
    def test_create_message(self):
        """Test message creation"""
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Hello doctor!"
        )
        
        self.assertEqual(message.room, self.chatroom)
        self.assertEqual(message.sender, self.patient_user)
        self.assertEqual(message.message, "Hello doctor!")
        self.assertFalse(message.read)
    
    def test_message_read_status(self):
        """Test message read status functionality"""
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Hello doctor!"
        )
        
        # Initially not read by doctor
        self.assertFalse(message.is_read_by(self.doctor_user))
        
        # Mark as read by doctor
        message.mark_as_read_by(self.doctor_user)
        self.assertTrue(message.is_read_by(self.doctor_user))
        
        # Should not mark own messages as read
        own_message = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="Hello patient!"
        )
        own_message.mark_as_read_by(self.doctor_user)
        self.assertFalse(own_message.is_read_by(self.doctor_user))
    
    def test_get_message_count(self):
        """Test getting message count in room"""
        # Initially no messages
        self.assertEqual(self.chatroom.get_message_count(), 0)
        
        # Add messages
        Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Message 1"
        )
        Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="Message 2"
        )
        
        self.assertEqual(self.chatroom.get_message_count(), 2)
    
    def test_get_last_message(self):
        """Test getting last message in room"""
        # Initially no messages
        self.assertIsNone(self.chatroom.get_last_message())
        
        # Add messages
        first_message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="First message"
        )
        
        last_message = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="Last message"
        )
        
        self.assertEqual(self.chatroom.get_last_message(), last_message)


class MessageReadStatusTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Dr. Test',
            role='doctor'
        )
        
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient Test',
            role='patient'
        )
        
        # Create profiles
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            gender='male',
            date_of_birth='1980-01-01',
            qualification='MBBS',
            specialty='General Practice',
            medical_registration_number='DOC123',
            prescriber_number='PRES123',
            provider_number='PROV123'
        )
        
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            gender='female',
            date_of_birth='1990-01-01',
            contact_address='123 Test St, Test City'
        )
        
        # Create appointment availability
        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor_user,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1),
            slot_type='long',
            timezone='UTC'
        )
        
        # Create appointment
        self.appointment = Appointment.objects.create(
            patient=self.patient_user,
            availability=self.availability,
            status='booked'
        )
        
        # Create chatroom
        self.chatroom = ChatRoom.objects.create(
            patient=self.patient_user,
            doctor=self.doctor_user,
            appointment=self.appointment
        )
        
        # Create message
        self.message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Test message"
        )
    
    def test_message_read_status_creation(self):
        """Test MessageReadStatus creation"""
        read_status = MessageReadStatus.objects.create(
            message=self.message,
            user=self.doctor_user
        )
        
        self.assertEqual(read_status.message, self.message)
        self.assertEqual(read_status.user, self.doctor_user)
        self.assertIsNotNone(read_status.read_at)
    
    def test_unique_constraint(self):
        """Test unique constraint on message and user"""
        # Create first read status
        MessageReadStatus.objects.create(
            message=self.message,
            user=self.doctor_user
        )
        
        # Try to create duplicate - should not raise error due to get_or_create usage
        # but let's test the constraint exists
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MessageReadStatus.objects.create(
                message=self.message,
                user=self.doctor_user
            )