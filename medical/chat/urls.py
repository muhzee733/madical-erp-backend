from django.urls import path
from .views import (
    ChatRoomListCreateView, 
    MessageListCreateView,
    MarkMessageAsReadView,
    MarkRoomMessagesAsReadView,
    UnreadCountView,
    RoomManagementView,
    RoomValidationView
)

urlpatterns = [
    path('rooms/', ChatRoomListCreateView.as_view(), name='chatroom-list'),
    path('messages/<int:room_id>/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:message_id>/mark-read/', MarkMessageAsReadView.as_view(), name='mark-message-read'),
    path('rooms/<int:room_id>/mark-all-read/', MarkRoomMessagesAsReadView.as_view(), name='mark-room-read'),
    path('rooms/<int:room_id>/manage/', RoomManagementView.as_view(), name='room-management'),
    path('rooms/validate/', RoomValidationView.as_view(), name='room-validation'),
    path('unread-count/', UnreadCountView.as_view(), name='unread-count'),
]
