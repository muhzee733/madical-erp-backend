from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import Message, ChatRoom, MessageReadStatus
from .serializers import MessageSerializer, ChatRoomSerializer
from users.permissions import IsDoctor, IsPatient
from .permissions import HasChatRoomAccess, CanCreateChatRoom, CanModifyMessage


class ChatRoomListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanCreateChatRoom]

    def get(self, request):
        user = request.user
        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        
        # Base queryset
        if user.role == 'doctor':
            rooms = ChatRoom.objects.filter(doctor=user)
        elif user.role == 'patient':
            rooms = ChatRoom.objects.filter(patient=user)
        elif user.role == 'admin':
            rooms = ChatRoom.objects.all()
        else:
            return Response({"detail": "Unauthorized user type."}, status=status.HTTP_403_FORBIDDEN)
        
        # Filter out deleted rooms unless specifically requested
        if not include_deleted:
            rooms = rooms.filter(is_deleted=False)
        
        # Optional status filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            rooms = rooms.filter(status=status_filter)
        
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        data = request.data
        
        # Validate required fields
        if not all(key in data for key in ['patient', 'doctor', 'appointment']):
            return Response(
                {"detail": "patient, doctor, and appointment are required fields."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the appointment and validate it exists
            from appointment.models import Appointment
            appointment = Appointment.objects.get(id=data['appointment'])
            
            # Validate that the appointment belongs to the specified patient and doctor
            if (appointment.patient.id != data['patient'] or 
                appointment.availability.doctor.id != data['doctor']):
                return Response(
                    {"detail": "Appointment does not match the specified patient and doctor."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Role-based creation validation
            if user.role == 'patient':
                # Patients can only create rooms for their own appointments
                if appointment.patient.id != user.id:
                    return Response(
                        {"detail": "Patients can only create chat rooms for their own appointments."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif user.role == 'doctor':
                # Doctors can only create rooms for appointments they're assigned to
                if appointment.availability.doctor.id != user.id:
                    return Response(
                        {"detail": "Doctors can only create chat rooms for their own appointments."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif user.role == 'admin':
                # Admins can create any room (no additional validation needed)
                pass
            else:
                return Response(
                    {"detail": "Unauthorized user role for room creation."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if room already exists for this appointment
            existing_room = ChatRoom.objects.filter(appointment=appointment).first()
            if existing_room:
                return Response(
                    {
                        "detail": "Chat room already exists for this appointment.",
                        "existing_room_id": existing_room.id
                    }, 
                    status=status.HTTP_409_CONFLICT
                )
            
            # Create the room
            serializer = ChatRoomSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                room = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"Error creating room: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageListCreateView(APIView):
    permission_classes = [IsAuthenticated, HasChatRoomAccess]

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
    permission_classes = [IsAuthenticated, CanModifyMessage]

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
    permission_classes = [IsAuthenticated, HasChatRoomAccess]

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
    permission_classes = [IsAuthenticated]

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


class RoomManagementView(APIView):
    """Manage room status (activate, deactivate, archive, delete)"""
    permission_classes = [IsAuthenticated, HasChatRoomAccess]

    def patch(self, request, room_id):
        """Update room status"""
        try:
            room = ChatRoom.objects.get(id=room_id)
            user = request.user
            
            # Validate room access
            if user.id != room.patient.id and user.id != room.doctor.id and user.role != 'admin':
                return Response({"detail": "Access denied to this room."}, status=status.HTTP_403_FORBIDDEN)
            
            action = request.data.get('action')
            if not action:
                return Response({"detail": "Action is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Only doctors and admins can manage room status
            if user.role not in ['doctor', 'admin']:
                return Response(
                    {"detail": "Only doctors and admins can manage room status."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if action == 'activate':
                if room.is_deleted:
                    return Response(
                        {"detail": "Cannot activate deleted room."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                room.status = 'active'
                room.save()
                message = "Room activated successfully."
                
            elif action == 'deactivate':
                room.deactivate()
                message = "Room deactivated successfully."
                
            elif action == 'archive':
                room.archive()
                message = "Room archived successfully."
                
            elif action == 'suspend':
                room.status = 'suspended'
                room.save()
                message = "Room suspended successfully."
                
            elif action == 'delete':
                # Only admins can delete rooms
                if user.role != 'admin':
                    return Response(
                        {"detail": "Only admins can delete rooms."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                room.soft_delete()
                message = "Room deleted successfully."
                
            else:
                return Response(
                    {"detail": "Invalid action. Valid actions: activate, deactivate, archive, suspend, delete"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                "message": message,
                "room_id": room_id,
                "new_status": room.status,
                "is_deleted": room.is_deleted
            }, status=status.HTTP_200_OK)
            
        except ChatRoom.DoesNotExist:
            return Response({"detail": "Room not found."}, status=status.HTTP_404_NOT_FOUND)


class RoomValidationView(APIView):
    """Validate room eligibility for an appointment"""
    permission_classes = [IsAuthenticated, CanCreateChatRoom]

    def post(self, request):
        """Check if a chat room can be created for an appointment"""
        appointment_id = request.data.get('appointment_id')
        if not appointment_id:
            return Response(
                {"detail": "appointment_id is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from appointment.models import Appointment
            appointment = Appointment.objects.get(id=appointment_id)
            user = request.user
            
            # Validate user has access to this appointment
            if user.role == 'patient' and appointment.patient.id != user.id:
                return Response(
                    {"detail": "Access denied to this appointment."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            elif user.role == 'doctor' and appointment.availability.doctor.id != user.id:
                return Response(
                    {"detail": "Access denied to this appointment."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check appointment status
            valid_statuses = ['booked', 'completed', 'rescheduled']
            if appointment.status not in valid_statuses:
                return Response({
                    "can_create": False,
                    "reason": f"Cannot create chat room for appointment with status: {appointment.status}",
                    "valid_statuses": valid_statuses
                }, status=status.HTTP_200_OK)
            
            # Check if room already exists
            existing_room = ChatRoom.objects.filter(appointment=appointment).first()
            if existing_room:
                return Response({
                    "can_create": False,
                    "reason": "Chat room already exists for this appointment",
                    "existing_room": {
                        "id": existing_room.id,
                        "status": existing_room.status,
                        "is_deleted": existing_room.is_deleted
                    }
                }, status=status.HTTP_200_OK)
            
            # All checks passed
            return Response({
                "can_create": True,
                "appointment": {
                    "id": appointment.id,
                    "patient": {
                        "id": appointment.patient.id,
                        "name": appointment.patient.get_full_name()
                    },
                    "doctor": {
                        "id": appointment.availability.doctor.id,
                        "name": appointment.availability.doctor.get_full_name()
                    },
                    "start_time": appointment.availability.start_time,
                    "status": appointment.status
                }
            }, status=status.HTTP_200_OK)
            
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
