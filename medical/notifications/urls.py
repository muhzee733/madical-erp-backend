from django.urls import path
from .views import ResendAppointmentConfirmationView, SendPrescriptionEmailView

urlpatterns = [
    path("appointment/confirm/", ResendAppointmentConfirmationView.as_view(), name="resend-appointment-confirmation"),
    path("prescription/send/", SendPrescriptionEmailView.as_view(), name="send-prescription-email"),
]
