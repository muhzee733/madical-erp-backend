import json
import urllib.parse
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from users.models import User
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Step 1: Validate JWT token
        user = await self.simple_jwt_auth()
        if not user:
            await self.close(code=4001)  # Authentication failed
            return
            
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = user

        # Step 2: Accept connection immediately
        await self.accept()
        
        # Step 3: Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'welcome',
            'message': f'Welcome to chat room {self.room_id}!',
            'user': user.email
        }))
        
        # Step 4: Add to group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                user_email = getattr(getattr(self, 'user', None), 'email', 'Unknown')
                room_id = getattr(self, 'room_id', 'Unknown')
                print(f"[Chat] User {user_email} disconnected from room {room_id}")
        except Exception as e:
            print(f"[WebSocket Error] Error during disconnect: {str(e)}")

    async def receive(self, text_data):
        try:
            # Parse JSON data
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_error('Invalid JSON format')
                return

            # Validate data structure
            if not isinstance(data, dict):
                await self.send_error('Message data must be an object')
                return

            # Extract and validate message
            message = data.get('message', '').strip()
            if not message:
                await self.send_error('Message cannot be empty')
                return

            # Validate message length (optional: prevent spam)
            if len(message) > 1000:  # Max 1000 characters
                await self.send_error('Message too long (max 1000 characters)')
                return

            # Use authenticated user instead of client-sent sender ID
            sender_id = getattr(self, 'user', None)
            if not sender_id:
                await self.send_error('User not authenticated')
                return
            sender_id = sender_id.id

            # Broadcast message to all room members immediately
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': sender_id,
                    'sender_name': getattr(self.user, 'first_name', 'User'),
                    'timestamp': 'now'
                }
            )

        except Exception as e:
            print(f"[WebSocket Error] Unexpected error in receive: {str(e)}")
            await self.send_error('An unexpected error occurred')

    async def send_error(self, error_message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error_message
        }))

    @database_sync_to_async
    def validate_room_access_and_status(self, user, room_id):
        """
        Validate if user has access to the chat room and if room allows messaging.
        """
        try:
            room = ChatRoom.objects.get(id=room_id)
            
            # Check access
            has_access = user.id == room.patient.id or user.id == room.doctor.id
            
            # Check if room allows messaging
            can_message = room.can_send_messages()
            
            return {
                'has_access': has_access,
                'can_message': can_message,
                'room_status': room.status,
                'is_deleted': room.is_deleted
            }
            
        except ChatRoom.DoesNotExist:
            return {
                'has_access': False,
                'can_message': False,
                'room_status': None,
                'is_deleted': None
            }
        except Exception as e:
            print(f"[Error validating room access]: {str(e)}")
            return {
                'has_access': False,
                'can_message': False,
                'room_status': None,
                'is_deleted': None
            }

    @database_sync_to_async
    def save_message(self, room_id, sender_id, message):
        """
        Save message to database with atomic transaction and comprehensive error handling
        Returns dict with message data on success, None on failure
        """
        from django.db import transaction
        
        try:
            # Use atomic transaction to ensure consistency
            with transaction.atomic():
                room = ChatRoom.objects.select_for_update().get(id=room_id)
                sender = User.objects.get(id=sender_id)
                
                # Double-check room access at database level
                if sender.id != room.patient.id and sender.id != room.doctor.id:
                    print(f"[Security] User {sender_id} attempted to send message to unauthorized room {room_id}")
                    return None
                
                # Create message within transaction
                msg = Message.objects.create(room=room, sender=sender, message=message)
                
                # Force commit by accessing the ID (ensures data is persisted)
                message_id = msg.id
                message_timestamp = msg.timestamp
                
                print(f"[Chat] Message committed: ID={message_id}, Room={room_id}, Sender={sender.email}")
                
                return {
                    'id': message_id,
                    'message': msg.message,
                    'sender_id': msg.sender.id,
                    'sender_name': msg.sender.first_name,
                    'timestamp': message_timestamp.isoformat(),
                    'room_id': msg.room.id
                }
            
        except ChatRoom.DoesNotExist:
            print(f"[Error] Chat room {room_id} does not exist")
            return None
        except User.DoesNotExist:
            print(f"[Error] User {sender_id} does not exist")
            return None
        except Exception as e:
            print(f"[Error] Failed to save message in transaction: {str(e)}")
            return None

    async def chat_message(self, event):
        """Send chat message to WebSocket client"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'id': event.get('message_id'),  # Database ID for client tracking
                'message': event['message'],
                'sender': event['sender'],
                'sender_name': event.get('sender_name', 'Unknown'),
                'timestamp': event.get('timestamp')
            }))
        except Exception as e:
            print(f"[WebSocket Error] Failed to send message: {str(e)}")
    
    async def simple_jwt_auth(self):
        """
        Simple JWT authentication - no complex database async operations
        """
        try:
            # Get token from query string
            query_string = self.scope.get('query_string', b'').decode()
            query_params = urllib.parse.parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            if not token:
                return None
            
            # Validate and decode token
            UntypedToken(token)
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            
            if not user_id:
                return None
            
            # Get user synchronously (avoiding async issues)
            user = await self.get_user_simple(user_id)
            return user
            
        except Exception:
            return None
    
    @database_sync_to_async
    def get_user_simple(self, user_id):
        """Simple synchronous user lookup"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    async def authenticate_jwt(self):
        """
        Simple JWT authentication from query string
        Returns User object if valid, None if invalid
        """
        try:
            # Get token from query string
            query_string = self.scope.get('query_string', b'').decode()
            query_params = urllib.parse.parse_qs(query_string)
            token = query_params.get('token', [None])[0]
            
            if not token:
                return None
            
            # Validate token structure
            UntypedToken(token)
            
            # Decode token
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            
            if not user_id:
                return None
            
            # Get user from database
            user = await self.get_user_by_id(user_id)
            return user
            
        except (InvalidToken, TokenError):
            return None
        except Exception:
            return None
    
    @database_sync_to_async
    def get_user_by_id(self, user_id):
        """Get user from database synchronously"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
