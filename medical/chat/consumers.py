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
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '').strip()
        
        if not message:
            # Send error for empty message
            await self.send(text_data=json.dumps({
                'error': 'Message cannot be empty'
            }))
            return

        # Use authenticated user instead of client-sent sender ID
        sender_id = self.user.id

        # Save to DB
        await self.save_message(self.room_id, sender_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender_id,
                'sender_name': self.user.first_name,
            }
        )

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
        
        try:
            print(f"Saving message: room={room_id}, sender={sender_id}, msg={message}")
            room = ChatRoom.objects.get(id=room_id)
            sender = User.objects.get(id=sender_id)
            msg = Message.objects.create(room=room, sender=sender, message=message)
            print("Message saved:", msg.id)
            return msg 
        except Exception as e:
            print("[Error Saving]", str(e))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'sender_name': event.get('sender_name', 'Unknown')
        }))
