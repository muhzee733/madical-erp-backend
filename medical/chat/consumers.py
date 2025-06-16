import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from users.models import User
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Check if user is authenticated
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return
            
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = user

        # Validate room access
        has_access = await self.validate_room_access(user, self.room_id)
        if not has_access:
            await self.close(code=4003)  # Forbidden
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                print(f"[Chat] User {getattr(self.user, 'email', 'Unknown')} disconnected from room {getattr(self, 'room_id', 'Unknown')}")
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
            sender_id = self.user.id

            # Save to DB with atomic transaction
            saved_message = await self.save_message(self.room_id, sender_id, message)
            if not saved_message:
                await self.send_error('Failed to save message')
                return

            # Message successfully persisted - now broadcast to all room members
            # Use data from saved message to ensure consistency
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': saved_message['message'],
                    'sender': saved_message['sender_id'],
                    'sender_name': saved_message['sender_name'],
                    'timestamp': saved_message['timestamp'],
                    'message_id': saved_message['id']  # Include DB ID for client tracking
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
    def validate_room_access(self, user, room_id):
        """
        Validate if user has access to the chat room.
        Only the patient and doctor assigned to the room can access it.
        """
        try:
            room = ChatRoom.objects.get(id=room_id)
            return user.id == room.patient.id or user.id == room.doctor.id
        except ChatRoom.DoesNotExist:
            return False
        except Exception as e:
            print(f"[Error validating room access]: {str(e)}")
            return False

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
