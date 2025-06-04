from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import permissions

from .models import User, DoctorProfile, PatientProfile
from .serializers import (
    AdminUserSerializer,
    UserSerializer,
    RegisterSerializer,
    DoctorProfileSerializer,
    PatientProfileSerializer,
)
from .permissions import IsPatient, IsDoctor, IsAdmin

# ──────────────── Login & Register ────────────────
class LoginView(APIView):
    class LoginSerializer(serializers.Serializer):
        email = serializers.CharField(max_length=100)
        password = serializers.CharField(write_only=True)

    def post(self, request):
        serializer = self.LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "User with this email does not exist"
                }, status=status.HTTP_200_OK)

            user = authenticate(email=user.email, password=password)

            if not user:
                return Response({
                    "message": "Incorrect password"
                }, status=status.HTTP_200_OK)

            if not user.is_active:
                return Response({
                    "message": "Your account is inactive"
                }, status=status.HTTP_200_OK)

            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            return Response({
                'access': str(access_token),
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        # set audit fields to self (user-created by self)
        user.created_by = user
        user.updated_by = user
        user.save()    

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        user_data = serializer.data
        return Response({
            "success": True,
            "message": "User registered successfully!",
            "user": user_data
        }, status=status.HTTP_201_CREATED)
    
# ──────────────── Doctor profile endpoints ────────────────
class DoctorProfileCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = DoctorProfileSerializer

    def perform_create(self, serializer):
        if self.request.user.role != "doctor":
            raise PermissionDenied("Only doctors can access this endpoint.")

        if hasattr(self.request.user, "doctorprofile"):
            raise serializers.ValidationError(
                "Doctor profile already exists. Use PATCH /profile/doctor/ to update it."
            )

        serializer.save(
            user=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class DoctorProfileDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = DoctorProfileSerializer

    def get_object(self):
        if self.request.user.role != "doctor":
            raise PermissionDenied("Only doctors can access this endpoint.")

        try:
            return self.request.user.doctorprofile
        except DoctorProfile.DoesNotExist:
            raise NotFound("Doctor profile not found. Create it with POST first.")

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

# ──────────────── Patient profile endpoints ────────────────
class PatientProfileCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = PatientProfileSerializer

    def perform_create(self, serializer):
        if self.request.user.role != "patient":
            raise ValidationError("Only patients can access this endpoint.")

        if hasattr(self.request.user, "patientprofile"):
            raise ValidationError(
                "Patient profile already exists. Use PATCH /profile/patient/ to update it."
            )

        serializer.save(
            user=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

class PatientProfileDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class   = PatientProfileSerializer

    def get_object(self):
        if self.request.user.role != "patient":
            raise PermissionDenied("Only patients can access this endpoint.")

        try:
            return self.request.user.patientprofile
        except PatientProfile.DoesNotExist:
            raise NotFound("Patient profile not found. Create it with POST first.")

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

# ──────────────── Admin endpoints ────────────────

class AdminDoctorProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DoctorProfileSerializer

    def get_object(self):
        doctor_id = self.kwargs.get("doctor_id")

        # Ensure the user exists and is a doctor
        user = get_object_or_404(User, id=doctor_id, role="doctor")

        # Ensure DoctorProfile exists
        try:
            return DoctorProfile.objects.get(user=user)
        except DoctorProfile.DoesNotExist:
            raise NotFound("Doctor profile not found for this user.")

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class AdminDoctorProfileListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DoctorProfileSerializer

    def get_queryset(self):
        return DoctorProfile.objects.select_related("user").order_by("id")

class AdminPatientProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = PatientProfileSerializer

    def get_object(self):
        patient_id = self.kwargs.get("patient_id")

        # Ensure the user exists and is a patient
        user = get_object_or_404(User, id=patient_id, role="patient")

        # Ensure PatientProfile exists
        try:
            return PatientProfile.objects.get(user=user)
        except PatientProfile.DoesNotExist:
            raise NotFound("Patient profile not found for this user.")

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class AdminPatientProfileListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = PatientProfileSerializer

    def get_queryset(self):
        return PatientProfile.objects.select_related("user").order_by("id")

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'id'

# ───── Get User by ID ───────────────────────────────
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

# ──────────────── Dashboards ────────────────

class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        return Response({
            "message": "Welcome to the Patient Dashboard",
            "user": {
                "email": request.user.email,
                "role": request.user.role
            }
        })

class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        return Response({
            "message": "Welcome to the Doctor Dashboard",
            "user": {
                "email": request.user.email,
                "role": request.user.role
            }
        })

class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({
            "message": "Welcome to the Admin Dashboard",
            "user": {
                "email": request.user.email,
                "role": request.user.role
            }
        })

