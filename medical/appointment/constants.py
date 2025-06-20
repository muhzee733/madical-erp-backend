# Appointment pricing constants
from decimal import Decimal

# New billing structure: flat fees based on patient history
NEW_PATIENT_FEE = Decimal('80.00')        # First-time patients pay $80
RETURNING_PATIENT_FEE = Decimal('50.00')  # Returning patients pay $50 regardless of appointment type

# Status options for determining patient history
COMPLETED_APPOINTMENT_STATUSES = ['booked', 'completed']