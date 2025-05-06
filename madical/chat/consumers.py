import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from users.models import User
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

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
        message = data['message']
        sender_id = data.get('sender')

        # Save to DB
        await self.save_message(self.room_name, sender_id, message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender_id,
            }
        )

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
            'sender': event['sender']
        }))
