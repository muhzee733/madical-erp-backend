from django.urls import path,include

urlpatterns = [
    path('api/v1/', include('users.urls')),
    path('api/v1/', include('questions.urls')),
    path('api/v1/', include('appointment.urls')),
    path('api/v1/', include('order.urls')),
    path('api/v1/', include('chat.urls')),
]
