from django.db import models

class EmailLog(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=50)  # e.g., sent, failed
    related_object_type = models.CharField(max_length=50, blank=True, null=True)  # e.g., prescription
    related_object_id = models.CharField(max_length=50, blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.recipient} ({self.status})"
