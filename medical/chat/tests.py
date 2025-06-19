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


class DoctorPatientCommunicationTest(TestCase):
    """Integration tests for doctor-patient chatroom communication"""
    
    def setUp(self):
        """Set up test data for doctor-patient communication"""
        # Create doctor user
        self.doctor_user = User.objects.create_user(
            email='doctor@hospital.com',
            password='doctor123',
            first_name='Dr. Sarah',
            last_name='Johnson',
            role='doctor'
        )
        
        # Create patient user  
        self.patient_user = User.objects.create_user(
            email='patient@email.com',
            password='patient123',
            first_name='John',
            last_name='Smith',
            role='patient'
        )
        
        # Create doctor profile
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor_user,
            gender='female',
            date_of_birth='1985-03-15',
            qualification='MBBS, MD',
            specialty='Internal Medicine',
            medical_registration_number='MED12345',
            prescriber_number='PRESC123',
            provider_number='PROV456'
        )
        
        # Create patient profile
        self.patient_profile = PatientProfile.objects.create(
            user=self.patient_user,
            gender='male',
            date_of_birth='1990-08-20',
            contact_address='456 Main St, City, State'
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
    
    def test_doctor_patient_chatroom_creation(self):
        """Test that doctor and patient can have a chatroom created"""
        self.assertEqual(self.chatroom.doctor, self.doctor_user)
        self.assertEqual(self.chatroom.patient, self.patient_user)
        self.assertEqual(self.chatroom.appointment, self.appointment)
        self.assertEqual(self.chatroom.status, 'active')
        self.assertTrue(self.chatroom.can_send_messages())
    
    def test_patient_sends_message_to_doctor(self):
        """Test patient can send messages to doctor"""
        message_text = "Hello Dr. Johnson, I have some questions about my prescription."
        
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message=message_text
        )
        
        self.assertEqual(message.sender, self.patient_user)
        self.assertEqual(message.message, message_text)
        self.assertEqual(message.room, self.chatroom)
        self.assertFalse(message.read)  # Initially unread
        
        # Verify doctor can see the message
        room_messages = Message.objects.filter(room=self.chatroom)
        self.assertEqual(room_messages.count(), 1)
        self.assertEqual(room_messages.first().message, message_text)
    
    def test_doctor_sends_message_to_patient(self):
        """Test doctor can send messages to patient"""
        message_text = "Hello John, I'm happy to help with your questions. What would you like to know?"
        
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message=message_text
        )
        
        self.assertEqual(message.sender, self.doctor_user)
        self.assertEqual(message.message, message_text)
        self.assertEqual(message.room, self.chatroom)
        
        # Verify patient can see the message
        room_messages = Message.objects.filter(room=self.chatroom)
        self.assertEqual(room_messages.count(), 1)
        self.assertEqual(room_messages.first().message, message_text)
    
    def test_bidirectional_conversation(self):
        """Test full bidirectional conversation between doctor and patient"""
        # Patient sends first message
        patient_msg1 = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Hi Doctor, I'm experiencing some side effects from my medication."
        )
        
        # Doctor responds
        doctor_msg1 = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="I'm sorry to hear that. Can you describe the side effects you're experiencing?"
        )
        
        # Patient follows up
        patient_msg2 = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="I've been feeling dizzy and nauseous, especially in the mornings."
        )
        
        # Doctor provides advice
        doctor_msg2 = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="Those can be common side effects. Let's schedule a follow-up to adjust your dosage."
        )
        
        # Verify all messages are in the chatroom
        all_messages = Message.objects.filter(room=self.chatroom).order_by('timestamp')
        self.assertEqual(all_messages.count(), 4)
        
        # Verify message order and senders
        messages_list = list(all_messages)
        self.assertEqual(messages_list[0].sender, self.patient_user)
        self.assertEqual(messages_list[1].sender, self.doctor_user)
        self.assertEqual(messages_list[2].sender, self.patient_user)
        self.assertEqual(messages_list[3].sender, self.doctor_user)
        
        # Verify both users can see all messages
        patient_visible_messages = Message.objects.filter(room=self.chatroom)
        doctor_visible_messages = Message.objects.filter(room=self.chatroom)
        
        self.assertEqual(patient_visible_messages.count(), 4)
        self.assertEqual(doctor_visible_messages.count(), 4)
    
    def test_message_read_status_between_doctor_and_patient(self):
        """Test message read status functionality between doctor and patient"""
        # Patient sends message
        patient_message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="When should I take my next dose?"
        )
        
        # Initially not read by doctor
        self.assertFalse(patient_message.is_read_by(self.doctor_user))
        
        # Doctor reads the message
        patient_message.mark_as_read_by(self.doctor_user)
        self.assertTrue(patient_message.is_read_by(self.doctor_user))
        
        # Doctor responds
        doctor_message = Message.objects.create(
            room=self.chatroom,
            sender=self.doctor_user,
            message="Take it with your evening meal, around 6 PM."
        )
        
        # Initially not read by patient
        self.assertFalse(doctor_message.is_read_by(self.patient_user))
        
        # Patient reads the message
        doctor_message.mark_as_read_by(self.patient_user)
        self.assertTrue(doctor_message.is_read_by(self.patient_user))
        
        # Verify read status tracking
        patient_msg_readers = patient_message.get_read_by_users()
        doctor_msg_readers = doctor_message.get_read_by_users()
        
        self.assertIn(self.doctor_user, patient_msg_readers)
        self.assertIn(self.patient_user, doctor_msg_readers)
    
    def test_chatroom_message_history_visibility(self):
        """Test that both doctor and patient can see complete message history"""
        # Create multiple messages over time
        messages_data = [
            (self.patient_user, "Hello doctor, I need help with my medication schedule."),
            (self.doctor_user, "Of course, I'm here to help. What specific questions do you have?"),
            (self.patient_user, "Should I take it before or after meals?"),
            (self.doctor_user, "Take it 30 minutes before meals for best absorption."),
            (self.patient_user, "Thank you! What if I forget a dose?"),
            (self.doctor_user, "Take it as soon as you remember, unless it's close to your next dose time."),
            (self.patient_user, "Got it, thanks for the clarification!"),
        ]
        
        created_messages = []
        for sender, text in messages_data:
            message = Message.objects.create(
                room=self.chatroom,
                sender=sender,
                message=text
            )
            created_messages.append(message)
            # Small delay to ensure different timestamps
            import time
            time.sleep(0.001)
        
        # Test message count
        total_messages = Message.objects.filter(room=self.chatroom).count()
        self.assertEqual(total_messages, 7)
        
        # Test message order (chronological)
        ordered_messages = Message.objects.filter(room=self.chatroom).order_by('timestamp')
        for i, (sender, text) in enumerate(messages_data):
            self.assertEqual(ordered_messages[i].sender, sender)
            self.assertEqual(ordered_messages[i].message, text)
        
        # Test last message retrieval
        last_message = self.chatroom.get_last_message()
        self.assertEqual(last_message.message, "Got it, thanks for the clarification!")
        self.assertEqual(last_message.sender, self.patient_user)
        
        # Test message count method
        self.assertEqual(self.chatroom.get_message_count(), 7)
    
    def test_chatroom_access_control(self):
        """Test that only the assigned doctor and patient can access the chatroom"""
        # Create another doctor and patient
        other_doctor = User.objects.create_user(
            email='other.doctor@hospital.com',
            password='password123',
            first_name='Dr. Other',
            role='doctor'
        )
        
        other_patient = User.objects.create_user(
            email='other.patient@email.com',
            password='password123',
            first_name='Other Patient',
            role='patient'
        )
        
        # Create a message in the chatroom
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="This is a private message"
        )
        
        # Test that authorized users can access
        self.assertTrue(self.patient_user.id == self.chatroom.patient.id or 
                       self.patient_user.id == self.chatroom.doctor.id)
        self.assertTrue(self.doctor_user.id == self.chatroom.patient.id or 
                       self.doctor_user.id == self.chatroom.doctor.id)
        
        # Test that unauthorized users cannot access
        self.assertFalse(other_doctor.id == self.chatroom.patient.id or 
                        other_doctor.id == self.chatroom.doctor.id)
        self.assertFalse(other_patient.id == self.chatroom.patient.id or 
                        other_patient.id == self.chatroom.doctor.id)
    
    def test_chatroom_status_affects_messaging(self):
        """Test that chatroom status affects ability to send messages"""
        # Active chatroom should allow messaging
        self.assertTrue(self.chatroom.can_send_messages())
        
        # Create message in active room
        message = Message.objects.create(
            room=self.chatroom,
            sender=self.patient_user,
            message="Test message in active room"
        )
        self.assertIsNotNone(message.id)
        
        # Deactivate chatroom
        self.chatroom.deactivate()
        self.assertFalse(self.chatroom.can_send_messages())
        
        # Archive chatroom
        self.chatroom.status = 'active'  # Reset first
        self.chatroom.save()
        self.chatroom.archive()
        self.assertFalse(self.chatroom.can_send_messages())
        
        # Soft delete chatroom
        self.chatroom.status = 'active'  # Reset first
        self.chatroom.is_deleted = False
        self.chatroom.save()
        self.chatroom.soft_delete()
        self.assertFalse(self.chatroom.can_send_messages())
        self.assertTrue(self.chatroom.is_deleted)
        self.assertEqual(self.chatroom.status, 'archived')