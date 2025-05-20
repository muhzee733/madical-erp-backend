import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings
import os

def initialize_firebase():
    # Path to your Firebase service account key file
    cred = credentials.Certificate(os.path.join(settings.BASE_DIR, 'firebase-credentials.json'))
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'YOUR_FIREBASE_DATABASE_URL'  # Replace with your Firebase database URL
    })

def get_chat_ref():
    return db.reference('/chats')

def get_online_status_ref():
    return db.reference('/online_status') 