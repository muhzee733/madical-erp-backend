from django.urls import path
from .views import RegisterView,LoginView,PatientDashboardView, DoctorDashboardView, AdminDashboardView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('dashboard/patient/', PatientDashboardView.as_view(), name='patient-dashboard'),
    path('dashboard/doctor/', DoctorDashboardView.as_view(), name='Doctor-dashboard'),
    path('dashboard/admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
