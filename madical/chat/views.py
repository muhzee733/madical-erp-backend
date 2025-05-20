from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from madical.firebase_config import get_chat_ref, get_online_status_ref
import time
from django.db import models

class ChatRoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        return ChatRoom.objects.filter(
            models.Q(patient=self.request.user) | models.Q(doctor=self.request.user)
        )

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        chat_room = self.get_object()
        message = request.data.get('message')
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Save message to Django database
        message_obj = Message.objects.create(
            room=chat_room,
            sender=request.user,
            message=message
        )

        # Save message to Firebase
        chat_ref = get_chat_ref()
        chat_ref.child(str(chat_room.id)).push({
            'message': message,
            'sender_id': request.user.id,
            'sender_name': request.user.username,
            'timestamp': time.time()
        })

        return Response(MessageSerializer(message_obj).data)

    @action(detail=True, methods=['post'])
    def update_online_status(self, request, pk=None):
        status_ref = get_online_status_ref()
        status_ref.child(str(request.user.id)).set({
            'status': request.data.get('status', 'online'),
            'last_seen': time.time()
        })
        return Response({'status': 'success'})

    @action(detail=True, methods=['get'])
    def get_messages(self, request, pk=None):
        chat_room = self.get_object()
        messages = Message.objects.filter(room=chat_room).order_by('timestamp')
        return Response(MessageSerializer(messages, many=True).data)
