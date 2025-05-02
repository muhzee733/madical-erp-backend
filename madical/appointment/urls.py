from django.urls import path
from .views import post_schedule, get_doctor_appointments, get_all_appointments

urlpatterns = [
    path('availabilities/', post_schedule, name='post-schedule'),
    path('availabilities/list/', get_doctor_appointments, name='get_doctor_appointments'),
    path('appointments/all/', get_all_appointments, name='get_all_appointments'),
]
