import os
import django 
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical.settings')
django.setup() 
load_dotenv()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
