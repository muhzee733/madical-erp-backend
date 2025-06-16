from rest_framework import permissions
from .models import ChatRoom, Message

class HasChatRoomAccess(permissions.BasePermission):
    """
    Custom permission to only allow users access to chat rooms they belong to.
    Patient and doctor can only access their own rooms.
    Admins can access all rooms.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin can access all rooms
        if user.role == 'admin':
            return True
        
        # For ChatRoom objects
        if isinstance(obj, ChatRoom):
            return user.id == obj.patient.id or user.id == obj.doctor.id
        
        # For Message objects, check room access
        if isinstance(obj, Message):
            room = obj.room
            return user.id == room.patient.id or user.id == room.doctor.id
        
        return False


class CanCreateChatRoom(permissions.BasePermission):
    """
    Permission for chat room creation.
    Only patients, doctors, and admins can create rooms.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Only allow specific roles to create rooms
        return request.user.role in ['patient', 'doctor', 'admin']


class CanModifyMessage(permissions.BasePermission):
    """
    Permission for message operations.
    Users can only modify (mark as read) messages in rooms they belong to.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin can modify any message
        if user.role == 'admin':
            return True
        
        # For Message objects, check room access
        if isinstance(obj, Message):
            room = obj.room
            return user.id == room.patient.id or user.id == room.doctor.id
        
        return False