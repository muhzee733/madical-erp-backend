from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .views import (
    ChatRoomListCreateView, 
    MessageListCreateView,
    MarkMessageAsReadView,
    MarkRoomMessagesAsReadView,
    UnreadCountView,
    RoomManagementView,
    RoomValidationView
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_root_view(request):
    """Chat API root endpoint"""
    return Response({
        "message": "Chat API endpoints",
        "endpoints": {
            "rooms": "/api/v1/chat/rooms/",
            "messages": "/api/v1/chat/messages/<room_id>/",
            "unread_count": "/api/v1/chat/unread-count/",
            "room_validation": "/api/v1/chat/rooms/validate/",
        }
    })

urlpatterns = [
    path('', chat_root_view, name='chat-root'),
    path('rooms/', ChatRoomListCreateView.as_view(), name='chatroom-list'),
    path('messages/<int:room_id>/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:message_id>/mark-read/', MarkMessageAsReadView.as_view(), name='mark-message-read'),
    path('rooms/<int:room_id>/mark-all-read/', MarkRoomMessagesAsReadView.as_view(), name='mark-room-read'),
    path('rooms/<int:room_id>/manage/', RoomManagementView.as_view(), name='room-management'),
    path('rooms/validate/', RoomValidationView.as_view(), name='room-validation'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
]
