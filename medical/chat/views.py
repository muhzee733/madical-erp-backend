from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import Message, ChatRoom, MessageReadStatus
from .serializers import MessageSerializer, ChatRoomSerializer
from users.permissions import IsDoctor, IsPatient


class ChatRoomListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsPatient]

    def get(self, request):
        user = request.user
        if user.role == 'doctor':
            rooms = ChatRoom.objects.filter(doctor=user)
        elif user.role == 'patient':
            rooms = ChatRoom.objects.filter(patient=user)
        else:
            return Response({"detail": "Unauthorized user type."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ChatRoomSerializer(rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ChatRoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor | IsPatient]

    def get(self, request, room_id):
        # Validate room access
        user = request.user
        try:
            room = ChatRoom.objects.get(id=room_id)
            if user.id != room.patient.id and user.id != room.doctor.id:
                return Response({"detail": "Access denied to this room."}, status=status.HTTP_403_FORBIDDEN)
        except ChatRoom.DoesNotExist:
            return Response({"detail": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

        messages = Message.objects.filter(room_id=room_id).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, room_id):
        # Validate room access before creating message
        user = request.user
        try:
            room = ChatRoom.objects.get(id=room_id)
            if user.id != room.patient.id and user.id != room.doctor.id:
                return Response({"detail": "Access denied to this room."}, status=status.HTTP_403_FORBIDDEN)
        except ChatRoom.DoesNotExist:
            return Response({"detail": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MessageSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(sender=request.user, room_id=room_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkMessageAsReadView(APIView):
    """Mark a specific message as read by the current user"""
    permission_classes = [IsAuthenticated, IsDoctor | IsPatient]

    def post(self, request, message_id):
        try:
            message = Message.objects.get(id=message_id)
            
            # Validate room access
            room = message.room
            user = request.user
            if user.id != room.patient.id and user.id != room.doctor.id:
                return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
            # Mark as read
            message.mark_as_read_by(user)
            
            return Response({
                "message": "Message marked as read",
                "message_id": message_id
            }, status=status.HTTP_200_OK)
            
        except Message.DoesNotExist:
            return Response({"detail": "Message not found."}, status=status.HTTP_404_NOT_FOUND)


class MarkRoomMessagesAsReadView(APIView):
    """Mark all messages in a room as read by the current user"""
    permission_classes = [IsAuthenticated, IsDoctor | IsPatient]

    def post(self, request, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id)
            user = request.user
            
            # Validate room access
            if user.id != room.patient.id and user.id != room.doctor.id:
                return Response({"detail": "Access denied to this room."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get unread messages by other users (not sent by current user)
            unread_messages = Message.objects.filter(
                room=room
            ).exclude(
                sender=user
            ).exclude(
                read_by__user=user
            )
            
            # Mark all as read
            marked_count = 0
            for message in unread_messages:
                message.mark_as_read_by(user)
                marked_count += 1
            
            return Response({
                "message": f"Marked {marked_count} messages as read",
                "room_id": room_id,
                "marked_count": marked_count
            }, status=status.HTTP_200_OK)
            
        except ChatRoom.DoesNotExist:
            return Response({"detail": "Room not found."}, status=status.HTTP_404_NOT_FOUND)


class UnreadCountView(APIView):
    """Get unread message count for current user"""
    permission_classes = [IsAuthenticated, IsDoctor | IsPatient]

    def get(self, request):
        user = request.user
        
        # Get rooms where user is either patient or doctor
        user_rooms = ChatRoom.objects.filter(
            Q(patient=user) | Q(doctor=user)
        )
        
        # Count unread messages (messages not sent by user and not marked as read)
        unread_count = Message.objects.filter(
            room__in=user_rooms
        ).exclude(
            sender=user
        ).exclude(
            read_by__user=user
        ).count()
        
        # Get unread count per room
        room_counts = {}
        for room in user_rooms:
            room_unread = Message.objects.filter(
                room=room
            ).exclude(
                sender=user
            ).exclude(
                read_by__user=user
            ).count()
            
            room_counts[room.id] = {
                "unread_count": room_unread,
                "room_info": {
                    "patient": room.patient.get_full_name(),
                    "doctor": room.doctor.get_full_name()
                }
            }
        
        return Response({
            "total_unread": unread_count,
            "rooms": room_counts
        }, status=status.HTTP_200_OK)
