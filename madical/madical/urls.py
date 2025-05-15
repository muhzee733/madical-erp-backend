from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({"message": "Welcome to ProMedicine API"})

urlpatterns = [
    path('', root_view),
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/questions/', include('questions.urls')),
    path('api/v1/appointments/', include('appointment.urls')),
    path('api/v1/orders/', include('order.urls')),
    path('api/v1/chat/', include('chat.urls')),
]
