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
    read = models.BooleanField(default=False)  # Keep for backward compatibility
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.first_name}: {self.message[:20]}"
    
    def is_read_by(self, user):
        """Check if message has been read by specific user"""
        return MessageReadStatus.objects.filter(message=self, user=user).exists()
    
    def mark_as_read_by(self, user):
        """Mark message as read by specific user"""
        if user != self.sender:  # Don't mark own messages as "read"
            MessageReadStatus.objects.get_or_create(message=self, user=user)
    
    def get_read_by_users(self):
        """Get list of users who have read this message"""
        return User.objects.filter(read_messages__message=self)


class MessageReadStatus(models.Model):
    """Track which users have read which messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_messages')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"{self.user.first_name} read: {self.message.message[:20]}"
