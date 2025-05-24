from rest_framework import serializers
from .models import User, DoctorProfile, PatientProfile

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={"input_type": "password"},
    )

    class Meta:
        model  = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "password",
            "role",
        )
        read_only_fields = ("id",)

    def validate_role(self, value):
        if value not in ("doctor", "patient"):
            raise serializers.ValidationError(
                "Role must be 'doctor' or 'patient'."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'is_active']

class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DoctorProfile
        fields = '__all__'
        read_only_fields = ('user','created_by','updated_by','created_at','updated_at')

class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PatientProfile
        fields = '__all__'
        read_only_fields = ('user','created_by','updated_by','created_at','updated_at')
