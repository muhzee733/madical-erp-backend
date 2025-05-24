from django.urls import path
from .views import post_schedule, get_doctor_appointments, get_all_appointments, get_appointment_details

urlpatterns = [
    path('availabilities/', post_schedule, name='post-schedule'),
    path('availabilities/list/', get_doctor_appointments, name='get_doctor_appointments'),
    path('all/', get_all_appointments, name='get_all_appointments'),
    path('details/<uuid:appointment_id>/', get_appointment_details, name='get_appointment_details'),
]
