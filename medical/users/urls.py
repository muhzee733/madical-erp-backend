from django.urls import path
from .views import (
    # auth
    RegisterView,
    LoginView,
    # dashboards
    PatientDashboardView,
    DoctorDashboardView,
    AdminDashboardView,
    # profile endpoints
    AdminUserListView,
    AdminUserDetailView,
    AdminDoctorProfileView,
    AdminPatientProfileView,
    DoctorProfileCreateView,
    DoctorProfileDetailView,
    PatientProfileCreateView,
    PatientProfileDetailView,
)

urlpatterns = [
    # ───── authentication ─────────────────────────────────────────
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",    LoginView.as_view(),    name="login"),

    # ───── Admin-level user management endpoints  ─────────

    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<int:id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    # Admin doctor & patient profile management
    path("admin/doctor-profile/<int:doctor_id>/", AdminDoctorProfileView.as_view(),
        name="admin-doctor-profile"),
    path("admin/patient-profile/<int:patient_id>/", AdminPatientProfileView.as_view(),
        name="admin-patient-profile"),

    # ───── doctor profile (create once, then view/update) ─────────
    path("profile/doctor/create/", DoctorProfileCreateView.as_view(),
         name="doctor-profile-create"),            # POST only
    path("profile/doctor/",          DoctorProfileDetailView.as_view(),
         name="doctor-profile"),                   # GET / PATCH

    # ───── patient profile ────────────────────────────────────────
    path("profile/patient/create/", PatientProfileCreateView.as_view(),
         name="patient-profile-create"),           # POST only
    path("profile/patient/",        PatientProfileDetailView.as_view(),
         name="patient-profile"),                  # GET / PATCH

    # ───── dashboards ─────────────────────────────────────────────
    path("dashboard/patient/", PatientDashboardView.as_view(),
         name="patient-dashboard"),
    path("dashboard/doctor/",  DoctorDashboardView.as_view(),
         name="doctor-dashboard"),
    path("dashboard/admin/",   AdminDashboardView.as_view(),
         name="admin-dashboard"),
]
