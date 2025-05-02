from rest_framework import serializers
from .models import Message, ChatRoom
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.first_name', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_name', 'message', 'timestamp']

class ChatRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ['id', 'patient', 'doctor', 'appointment', 'created_at']
