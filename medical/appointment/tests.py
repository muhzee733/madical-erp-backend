from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from django.utils.timezone import now, timedelta
from users.models import User
from appointment.models import AppointmentActionLog, AppointmentAvailability, Appointment
import pytz
import uuid

class AvailabilityFullTestSuite(APITestCase):
    def setUp(self):
        AppointmentAvailability.objects.all().delete()
        Appointment.objects.all().delete()        

        self.tz = pytz.timezone('Australia/Brisbane')
        self.doctor = User.objects.create_user(email='doc@example.com', password='testpass', role='doctor', first_name='Doc')
        self.patient = User.objects.create_user(email='pat@example.com', password='testpass', role='patient')
        self.client = APIClient()

    def create_availability(self, doctor, start=None, end=None):
        if not start:
            start = now() + timedelta(days=1)
        if not end:
            end = start + timedelta(minutes=15)
        return AppointmentAvailability.objects.create(
            doctor=doctor,
            start_time=start,
            end_time=end,
            slot_type='short',
            timezone='Australia/Brisbane'
        )

    # ───── POST /availabilities/ ─────

    def test_doctor_can_create_valid_availability(self):
        self.client.force_authenticate(user=self.doctor)
        start = now() + timedelta(days=1)
        end = start + timedelta(minutes=15)
        response = self.client.post(reverse('create-availability'), {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 201)

    def test_cannot_create_slot_in_past(self):
        self.client.force_authenticate(user=self.doctor)
        start = now() - timedelta(hours=1)
        end = start + timedelta(minutes=15)
        response = self.client.post(reverse('create-availability'), {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_cannot_create_slot_with_start_after_end(self):
        self.client.force_authenticate(user=self.doctor)
        start = now() + timedelta(days=1)
        end = start - timedelta(minutes=5)
        response = self.client.post(reverse('create-availability'), {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 400)

    # ───── POST /availabilities/bulk/ ─────

    def test_valid_bulk_creation(self):
        self.client.force_authenticate(user=self.doctor)
        today = now().date()
        response = self.client.post(reverse('bulk-availability'), {
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "days_of_week": [today.strftime("%A")],
            "start_time": "09:00",
            "end_time": "10:00",
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn("slots created", response.data["message"])

    def test_bulk_creation_skips_existing_slots(self):
        self.client.force_authenticate(user=self.doctor)
        start = now().replace(hour=9, minute=0, second=0, microsecond=0)
        self.create_availability(self.doctor, start, start + timedelta(minutes=15))
        response = self.client.post(reverse('bulk-availability'), {
            "start_date": start.date().isoformat(),
            "end_date": start.date().isoformat(),
            "days_of_week": [start.strftime("%A")],
            "start_time": "09:00",
            "end_time": "09:30",
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn("slots created", response.data["message"])

    def test_patient_cannot_access_bulk_creation(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('bulk-availability'), {}, format='json')
        self.assertEqual(response.status_code, 403)

    # ───── GET /availabilities/list/ ─────

    def test_doctor_can_list_their_availabilities(self):
        self.create_availability(self.doctor)
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse('list-my-availabilities'))
        self.assertEqual(response.status_code, 200)

        # Paginated result
        self.assertGreaterEqual(len(response.data['results']), 1)
        for slot in response.data['results']:
            self.assertEqual(slot['doctor'], self.doctor.id)

    # ───── PUT /availabilities/<pk>/ ─────

    def test_doctor_can_update_unbooked_availability(self):
        availability = self.create_availability(self.doctor)
        self.client.force_authenticate(user=self.doctor)
        response = self.client.put(reverse('edit-availability', args=[availability.id]), {
            "start_time": (availability.start_time + timedelta(hours=1)).isoformat(),
            "end_time": (availability.end_time + timedelta(hours=1)).isoformat(),
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 200)

    def test_update_fails_on_booked_slot(self):
        availability = self.create_availability(self.doctor)
        availability.is_booked = True
        availability.save()
        self.client.force_authenticate(user=self.doctor)
        response = self.client.put(reverse('edit-availability', args=[availability.id]), {
            "start_time": (availability.start_time + timedelta(hours=1)).isoformat(),
            "end_time": (availability.end_time + timedelta(hours=1)).isoformat(),
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 400)

    # ───── DELETE /availabilities/<pk>/ ─────

    def test_delete_unbooked_availability(self):
        availability = self.create_availability(self.doctor)
        self.client.force_authenticate(user=self.doctor)
        response = self.client.delete(reverse('delete-availability', args=[availability.id]))
        self.assertEqual(response.status_code, 204)

    def test_delete_fails_on_booked_slot(self):
        availability = self.create_availability(self.doctor)
        availability.is_booked = True
        availability.save()
        self.client.force_authenticate(user=self.doctor)
        response = self.client.delete(reverse('delete-availability', args=[availability.id]))
        self.assertEqual(response.status_code, 400)


class AppointmentBookingAndCancellationTests(APITestCase):
    def setUp(self):
        AppointmentAvailability.objects.all().delete()
        Appointment.objects.all().delete()
        AppointmentActionLog.objects.all().delete()

        self.client = APIClient()
        self.tz = pytz.timezone('Australia/Brisbane')

        self.doctor = User.objects.create_user(
            email='doc@example.com',
            password='testpass',
            role='doctor',
            first_name='Doc'  # needed for filtering
        )

        self.patient = User.objects.create_user(
            email='pat@example.com',
            password='testpass',
            role='patient'
        )

        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='testpass',
            role='admin',
            is_superuser=True
        )

        self.future_start = now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.future_end = self.future_start + timedelta(minutes=15)

        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=self.future_start,
            end_time=self.future_end,
            slot_type='short', 
            timezone='Australia/Brisbane',
            is_booked=False
        )

    # ------------------- GET /appointments/all/ -------------------

    def test_patient_sees_only_future_available_slots(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('list-available-appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(not slot['is_booked'] for slot in response.data['results']))

    def test_filtering_available_slots(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('list-available-appointments'), {
            "doctor_name": "doc",
            "slot_type": "short",
            "date_from": self.future_start.date().isoformat(),
            "date_to": self.future_end.date().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)

    # ------------------- POST /appointments/ -------------------

    def test_patient_can_book_valid_slot(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.availability.refresh_from_db()
        self.assertTrue(self.availability.is_booked)

    def test_booking_already_booked_slot_returns_error(self):
        self.availability.is_booked = True
        self.availability.save()

        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_double_booking_same_time_is_prevented(self):
        self.client.force_authenticate(user=self.patient)
        self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')

        overlap_start = self.future_start + timedelta(minutes=5)
        overlap_end = overlap_start + timedelta(minutes=15)
        overlap_slot = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=overlap_start,
            end_time=overlap_end,
            slot_type='short',
            timezone='Australia/Brisbane'
        )

        response = self.client.post(reverse('book-appointment'), {
            "availability": str(overlap_slot.id)
        }, format='json')
        self.assertEqual(response.status_code, 400)

    # ------------------- GET /appointments/my/ -------------------

    def test_patient_sees_own_appointments(self):
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        response = self.client.get(reverse('list-my-appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data['results'][0]['patient']['id'], self.patient.id)

    def test_doctor_sees_own_appointments(self):
        self.client.force_authenticate(user=self.patient)
        self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')

        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(reverse('list-my-appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(str(response.data['results'][0]['availability']), str(self.availability.id))

    # ------------------- POST /appointments/<id>/cancel/ -------------------

    def test_patient_can_cancel_appointment_over_1hr(self):
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        appointment_id = book_response.data['id']

        cancel_url = reverse('cancel-appointment', args=[appointment_id])
        cancel_response = self.client.post(cancel_url)
        self.assertEqual(cancel_response.status_code, 200)

        self.availability.refresh_from_db()
        self.assertFalse(self.availability.is_booked)

        self.assertTrue(AppointmentActionLog.objects.filter(appointment_id=appointment_id, action_type='cancelled').exists())

    def test_patient_cannot_cancel_within_1hr(self):
        close_start = now() + timedelta(minutes=59)
        close_end = close_start + timedelta(minutes=15)
        close_availability = AppointmentAvailability.objects.create(
            doctor=self.doctor, start_time=close_start, end_time=close_end,
            slot_type="short", timezone="Australia/Brisbane", is_booked=False
        )
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(close_availability.id)
        }, format='json')
        appointment_id = book_response.data['id']

        cancel_url = reverse('cancel-appointment', args=[appointment_id])
        cancel_response = self.client.post(cancel_url)
        self.assertEqual(cancel_response.status_code, 400)

    def test_doctor_can_cancel_anytime(self):
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        appointment_id = book_response.data['id']

        self.client.force_authenticate(user=self.doctor)
        cancel_response = self.client.post(reverse('cancel-appointment', args=[appointment_id]))
        self.assertEqual(cancel_response.status_code, 200)

    def test_admin_can_cancel_anytime(self):
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        appointment_id = book_response.data['id']

        self.client.force_authenticate(user=self.admin)
        cancel_response = self.client.post(reverse('cancel-appointment', args=[appointment_id]))
        self.assertEqual(cancel_response.status_code, 200)


class AppointmentRescheduleAndStatusTests(APITestCase):
    def setUp(self):
        AppointmentAvailability.objects.all().delete()
        Appointment.objects.all().delete()
        AppointmentActionLog.objects.all().delete()

        self.client = APIClient()
        self.tz = pytz.timezone('Australia/Brisbane')

        self.doctor = User.objects.create_user(email='doc@example.com', password='testpass', role='doctor', first_name='Doc')
        self.patient = User.objects.create_user(email='pat@example.com', password='testpass', role='patient')
        self.admin = User.objects.create_user(email='admin@example.com', password='testpass', role='admin', is_superuser=True)

        self.start1 = now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.end1 = self.start1 + timedelta(minutes=15)
        self.start2 = self.start1 + timedelta(minutes=30)
        self.end2 = self.start2 + timedelta(minutes=15)

        self.original_slot = AppointmentAvailability.objects.create(
            doctor=self.doctor, start_time=self.start1, end_time=self.end1,
            slot_type="short", timezone="Australia/Brisbane", is_booked=False
        )
        self.new_slot = AppointmentAvailability.objects.create(
            doctor=self.doctor, start_time=self.start2, end_time=self.end2,
            slot_type="short", timezone="Australia/Brisbane", is_booked=False
        )

        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.original_slot.id)
        }, format='json')
        self.original_appointment_id = response.data["id"]

    # ------------------- RESCHEDULE -------------------

    def test_patient_can_reschedule_to_unbooked_slot(self):
        response = self.client.post(reverse('reschedule-appointment', args=[self.original_appointment_id]), {
            "new_availability_id": str(self.new_slot.id)
        }, format='json')
        self.assertEqual(response.status_code, 200)

        new_appointment = Appointment.objects.get(availability=self.new_slot)
        old_appointment = Appointment.objects.get(id=self.original_appointment_id)

        self.assertEqual(old_appointment.status, "rescheduled")
        self.assertEqual(new_appointment.rescheduled_from, old_appointment)
        self.assertTrue(AppointmentActionLog.objects.filter(appointment=new_appointment, action_type="rescheduled").exists())

    def test_cannot_reschedule_to_already_booked_slot(self):
        self.new_slot.is_booked = True
        self.new_slot.save()

        response = self.client.post(reverse('reschedule-appointment', args=[self.original_appointment_id]), {
            "new_availability_id": str(self.new_slot.id)
        }, format='json')
        self.assertEqual(response.status_code, 404)

    # ------------------- COMPLETE -------------------

    def test_doctor_can_mark_appointment_completed(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(reverse('complete-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AppointmentActionLog.objects.filter(appointment_id=self.original_appointment_id, action_type="completed").exists())

    def test_admin_can_mark_appointment_completed(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('complete-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 200)

    def test_patient_cannot_mark_completed(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('complete-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 403)

    # ------------------- NO-SHOW -------------------

    def test_doctor_can_mark_appointment_no_show(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(reverse('no-show-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AppointmentActionLog.objects.filter(appointment_id=self.original_appointment_id, action_type="no_show").exists())

    def test_admin_can_mark_appointment_no_show(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('no-show-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 200)

    def test_patient_cannot_mark_no_show(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(reverse('no-show-appointment', args=[self.original_appointment_id]))
        self.assertEqual(response.status_code, 403)


class AuditLogAndSecurityTests(APITestCase):
    def setUp(self):
        AppointmentAvailability.objects.all().delete()
        Appointment.objects.all().delete()
        AppointmentActionLog.objects.all().delete()

        self.client = APIClient()
        self.tz = pytz.timezone('Australia/Brisbane')

        self.doctor = User.objects.create_user(email='doc@example.com', password='testpass', role='doctor', first_name='Doc')
        self.patient = User.objects.create_user(email='pat@example.com', password='testpass', role='patient')
        self.admin = User.objects.create_user(email='admin@example.com', password='testpass', role='admin', is_superuser=True)

        self.start = now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.end = self.start + timedelta(minutes=15)

        self.availability = AppointmentAvailability.objects.create(
            doctor=self.doctor,
            start_time=self.start,
            end_time=self.end,
            slot_type='short',
            timezone='Australia/Brisbane'
        )

        # Book appointment
        self.client.force_authenticate(user=self.patient)
        book_response = self.client.post(reverse('book-appointment'), {
            "availability": str(self.availability.id)
        }, format='json')
        self.appointment_id = book_response.data["id"]

        # Add log manually
        AppointmentActionLog.objects.create(
            appointment_id=self.appointment_id,
            action_type="created",
            performed_by=self.patient
        )

    # ------------------- AUDIT LOGS -------------------

    def test_logs_are_shown_for_appointment(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse('appointment-logs', args=[self.appointment_id]))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['action_type'], 'created')

    def test_unauthorized_user_cannot_access_logs(self):
        self.client.logout()
        response = self.client.get(reverse('appointment-logs', args=[self.appointment_id]))
        self.assertEqual(response.status_code, 401)

    # ------------------- SECURITY & EDGE CASES -------------------

    def test_unauthenticated_access_is_rejected(self):
        self.client.logout()
        endpoints = [
            reverse('list-available-appointments'),
            reverse('book-appointment'),
            reverse('list-my-appointments'),
            reverse('appointment-logs', args=[self.appointment_id])
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401)

    def test_patient_cannot_delete_availability(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.delete(reverse('delete-availability', args=[self.availability.id]))
        self.assertEqual(response.status_code, 403)

    def test_invalid_uuid_returns_404(self):
        self.client.force_authenticate(user=self.doctor)
        bad_uuid = uuid.uuid4()
        response = self.client.get(reverse('appointment-logs', args=[bad_uuid]))
        self.assertEqual(response.status_code, 404)

    def test_malformed_datetime_data_returns_400(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(reverse('create-availability'), {
            "start_time": "not-a-datetime",
            "end_time": "also-not-valid",
            "slot_type": "short",
            "timezone": "Australia/Brisbane"
        }, format='json')
        self.assertEqual(response.status_code, 400)
