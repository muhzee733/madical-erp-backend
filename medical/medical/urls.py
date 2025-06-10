from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from prescriptions.views import DrugListCreateView, DrugDetailView

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
    path('api/v1/drugs/', DrugListCreateView.as_view(), name='drug-list-create'),
    path('api/v1/drugs/<int:pk>/', DrugDetailView.as_view(), name='drug-detail'),
    path('api/v1/prescriptions/', include('prescriptions.urls')),
    path('api/v1/supplier-products/', include('supplier_products.urls')),
    path("api/v1/notifications/", include("notifications.urls")),
]
