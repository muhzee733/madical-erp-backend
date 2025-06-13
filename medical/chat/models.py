from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatRoom(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_rooms')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_rooms')
    appointment = models.OneToOneField('appointment.Appointment', on_delete=models.CASCADE)  # changed to Appointment
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active')

    def __str__(self):
        return f"Room: {self.patient.first_name} ↔ {self.doctor.first_name}"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.first_name}: {self.message[:20]}"
