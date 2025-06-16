from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatRoom(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
        ('suspended', 'Suspended'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_rooms')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_rooms')
    appointment = models.OneToOneField('appointment.Appointment', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Room: {self.patient.first_name} ↔ {self.doctor.first_name}"
    
    def clean(self):
        """Validate room data"""
        from django.core.exceptions import ValidationError
        
        # Validate user roles
        if self.patient.role != 'patient':
            raise ValidationError({'patient': 'Selected user is not a patient.'})
        
        if self.doctor.role != 'doctor':
            raise ValidationError({'doctor': 'Selected user is not a doctor.'})
        
        # Validate appointment relationships
        if hasattr(self, 'appointment') and self.appointment:
            if self.appointment.patient != self.patient:
                raise ValidationError({
                    'appointment': 'Appointment patient does not match room patient.'
                })
            
            if self.appointment.availability.doctor != self.doctor:
                raise ValidationError({
                    'appointment': 'Appointment doctor does not match room doctor.'
                })
            
            # Validate appointment status for room creation
            valid_statuses = ['booked', 'completed', 'rescheduled']
            if self.appointment.status not in valid_statuses:
                raise ValidationError({
                    'appointment': f'Cannot create chat room for appointment with status: {self.appointment.status}'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)
    
    def deactivate(self):
        """Deactivate the room"""
        self.status = 'inactive'
        self.save()
    
    def archive(self):
        """Archive the room"""
        self.status = 'archived'
        self.save()
    
    def soft_delete(self):
        """Soft delete the room"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.status = 'archived'
        self.save()
    
    def can_send_messages(self):
        """Check if messages can be sent in this room"""
        return self.status == 'active' and not self.is_deleted
    
    def get_message_count(self):
        """Get total message count in room"""
        return self.messages.filter(room=self).count()
    
    def get_last_message(self):
        """Get the last message in the room"""
        return self.messages.filter(room=self).order_by('-timestamp').first()

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
