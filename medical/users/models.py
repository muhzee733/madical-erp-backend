from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
import uuid

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('not_specified', 'Prefer not to say')
]

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role='patient', **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('first_name', 'Super')
        extra_fields.setdefault('last_name', 'User')
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    created_by = models.ForeignKey(
        'self',
        null=True, blank=True,
        related_name='users_created',
        on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        'self',
        null=True, blank=True,
        related_name='users_updated',
        on_delete=models.SET_NULL
    )
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role']

    def __str__(self):
        return f"{self.email} ({self.role})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    qualification = models.CharField(max_length=255)
    specialty = models.CharField(max_length=100)
    medical_registration_number = models.CharField(max_length=50, unique=True)
    registration_expiry = models.DateField(null=True, blank=True)
    prescriber_number = models.CharField(max_length=50, unique=True)
    provider_number = models.CharField(max_length=50, unique=True)
    hpi_i = models.CharField(max_length=16, blank=True, null=True, unique=True)
    digital_signature = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='doctorprofile_created',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='doctorprofile_updated',
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.specialty})"

    @property
    def full_name(self):
        return self.user.get_full_name()

class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    contact_address = models.TextField()
    medicare_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    irn = models.CharField(max_length=10, blank=True, null=True)
    medicare_expiry = models.DateField(blank=True, null=True)
    ihi = models.CharField(max_length=16, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="patientprofile_created",
        null=True, blank=True, on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="patientprofile_updated",
        null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"

    @property
    def full_name(self):
        return self.user.get_full_name()