from rest_framework import status, serializers
from .serializers import RegisterSerializer, AdminUserSerializer
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .permissions import IsPatient, IsDoctor, IsAdmin
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

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

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        user_data = serializer.data
        return Response({
            "success": True,
            "message": "User registered successfully!",
            "user": user_data
        }, status=status.HTTP_201_CREATED)

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
            "message": "Welcome",
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

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().order_by('id')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'id'
