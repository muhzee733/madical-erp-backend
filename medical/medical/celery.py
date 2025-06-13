import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical.settings')

app = Celery('medical')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()