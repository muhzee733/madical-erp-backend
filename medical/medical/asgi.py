import os
import django 
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical.settings')
django.setup() 
load_dotenv()

from channels.routing import ProtocolTypeRouter, URLRouter
from chat.middleware import JWTAuthMiddlewareStack
import chat.routing

from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})
