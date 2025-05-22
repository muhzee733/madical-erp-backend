from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Message, ChatRoom
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
        messages = Message.objects.filter(room_id=room_id).order_by('timestamp')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, room_id):
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(sender=request.user, room_id=room_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
