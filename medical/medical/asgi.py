import os
import django 
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical.settings')
django.setup() 
load_dotenv()

from django.core.asgi import get_asgi_application

application = get_asgi_application()