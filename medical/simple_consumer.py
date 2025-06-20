"""
Simple WebSocket consumer for debugging
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SimpleDebugConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"[DEBUG] WebSocket connection attempt")
        print(f"[DEBUG] Scope: {self.scope}")
        print(f"[DEBUG] User: {self.scope.get('user')}")
        
        # Accept connection immediately for debugging
        await self.accept()
        
        # Send debug info
        await self.send(text_data=json.dumps({
            'type': 'debug',
            'message': 'Connection successful!',
            'user': str(self.scope.get('user')),
            'path': self.scope.get('path'),
            'query_string': self.scope.get('query_string', b'').decode()
        }))

    async def disconnect(self, close_code):
        print(f"[DEBUG] WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        print(f"[DEBUG] Received: {text_data}")
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'message': f'Echo: {text_data}'
        }))