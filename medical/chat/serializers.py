from rest_framework import serializers
from .models import Message, ChatRoom, MessageReadStatus
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.first_name', read_only=True)
    is_read = serializers.SerializerMethodField()
    read_by_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_name', 'message', 'timestamp', 'is_read', 'read_by_count']
        read_only_fields = ['id', 'room', 'sender', 'sender_name', 'timestamp', 'is_read', 'read_by_count']

    def get_is_read(self, obj):
        """Check if current user has read this message"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_read_by(request.user)
        return False
    
    def get_read_by_count(self, obj):
        """Get count of users who have read this message"""
        return obj.read_by.count()

class ChatRoomSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    appointment_details = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'patient', 'doctor', 'appointment', 'created_at', 'updated_at', 
                  'status', 'is_deleted', 'deleted_at', 'patient_name', 'doctor_name', 
                  'appointment_details', 'unread_count']
        read_only_fields = ['created_at', 'updated_at', 'deleted_at', 'patient_name', 
                           'doctor_name', 'appointment_details', 'unread_count']
        
    def get_appointment_details(self, obj):
        """Get basic appointment information"""
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'start_time': obj.appointment.availability.start_time,
                'end_time': obj.appointment.availability.end_time,
                'status': obj.appointment.status
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user in this room"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            return Message.objects.filter(
                room=obj
            ).exclude(
                sender=user
            ).exclude(
                read_by__user=user
            ).count()
        return 0
    
    def validate(self, data):
        """Validate that patient, doctor, and appointment are consistent"""
        if 'appointment' in data and 'patient' in data and 'doctor' in data:
            appointment = data['appointment']
            
            # Check that appointment patient matches specified patient
            if appointment.patient != data['patient']:
                raise serializers.ValidationError(
                    "Patient must match the appointment's patient."
                )
            
            # Check that appointment doctor matches specified doctor
            if appointment.availability.doctor != data['doctor']:
                raise serializers.ValidationError(
                    "Doctor must match the appointment's doctor."
                )
            
            # Check if room already exists for this appointment
            existing_room = ChatRoom.objects.filter(appointment=appointment).first()
            if existing_room:
                raise serializers.ValidationError(
                    f"Chat room already exists for this appointment (Room ID: {existing_room.id})."
                )
        
        return data
