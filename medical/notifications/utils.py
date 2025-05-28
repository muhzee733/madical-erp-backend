from django.core.mail import send_mail
from django.conf import settings
from .models import EmailLog


def send_prescription_email(to_email, subject, body, related_id=None):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        status = "sent"
    except Exception as e:
        status = f"failed: {str(e)}"

    # Log the email
    EmailLog.objects.create(
        recipient=to_email,
        subject=subject,
        message=body,
        status=status,
        related_object_type="prescription",
        related_object_id=str(related_id) if related_id else None,
    )


def send_appointment_confirmation(to_email, subject, body, related_id=None):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        status = "sent"
    except Exception as e:
        status = f"failed: {str(e)}"

    # Log the email
    EmailLog.objects.create(
        recipient=to_email,
        subject=subject,
        message=body,
        status=status,
        related_object_type="appointment",
        related_object_id=str(related_id) if related_id else None,
    )
