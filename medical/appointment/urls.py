from django.urls import path
from . import views

urlpatterns = [
    # ──────────────── Doctor Availability ────────────────
    path('availabilities/', views.CreateAvailabilityView.as_view(), name='create-availability'),
    path('availabilities/bulk/', views.BulkAvailabilityView.as_view(), name='bulk-availability'),
    path("appointments/availabilities/custom/", views.CustomAvailabilityView.as_view(), name="custom-availability"),
    path('availabilities/list/', views.ListMyAvailabilityView.as_view(), name='list-my-availabilities'),
    path('availabilities/<uuid:pk>/', views.EditAvailabilityView.as_view(), name='edit-availability'),
    path('availabilities/<uuid:pk>/delete/', views.DeleteAvailabilityView.as_view(), name='delete-availability'),

    # ──────────────── Patient: Available Slots & Booking ────────────────
    path('all/', views.ListAvailableAppointmentsView.as_view(), name='list-available-appointments'),
    path('', views.BookAppointmentView.as_view(), name='book-appointment'),

    # ──────────────── Appointment Management ────────────────
    path('<uuid:pk>/update/', views.UpdateAppointmentView.as_view(), name='update-appointment'),
    path('<uuid:appointment_id>/cancel/', views.CancelAppointmentView.as_view(), name='cancel-appointment'),
    path('<uuid:appointment_id>/reschedule/', views.RescheduleAppointmentView.as_view(), name='reschedule-appointment'),
    path('my/', views.ListMyAppointmentsView.as_view(), name='list-my-appointments'),

    # ──────────────── Doctor: Update Appointment Status ────────────────
    path('<uuid:appointment_id>/complete/', views.MarkAppointmentCompleteView.as_view(), name='complete-appointment'),
    path('<uuid:appointment_id>/no-show/', views.MarkAppointmentNoShowView.as_view(), name='no-show-appointment'),

    # ──────────────── Doctor: View Appointment ────────────────
    path('<uuid:appointment_id>/participants/', views.AppointmentPartyInfoView.as_view(), name='appointment-participants'),

    # ──────────────── Logs / Audit ────────────────
    path('<uuid:appointment_id>/logs/', views.AppointmentLogView.as_view(), name='appointment-logs'),
    path('<uuid:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
]
