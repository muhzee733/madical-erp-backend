from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from prescriptions.models import Drug, Prescription, PrescriptionDrug, PrescriptionSupplierProduct
from supplier_products.models import SupplierProduct


class PrescriptionViewTests(APITestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(email="doctor@example.com", password="pass123", role="doctor")
        self.patient = User.objects.create_user(email="patient@example.com", password="pass123", role="patient")
        self.other_patient = User.objects.create_user(email="someone@example.com", password="pass123", role="patient")

        self.drug = Drug.objects.create(pbs_code="DR123", drug_name="Panadol")
        self.product = SupplierProduct.objects.create(brand_name="CBD Oil", generic_name="Cannabis")

        self.prescription_url = reverse("prescription-create")
        self.list_url = reverse("prescription-list")

        self.client.force_authenticate(user=self.doctor)

    def test_create_prescription_success(self):
        payload = {
            "patient": self.patient.id,
            "notes": "Treatment plan for pain",
            "prescribed_drugs": [{
                "drug": self.drug.id,
                "dosage": "1 tablet",
                "instructions": "Take after food",
                "quantity": 1,
                "repeats": 0
            }],
            "prescribed_supplier_products": [{
                "product": self.product.id,
                "dosage": "Apply twice daily",
                "instructions": "For relief",
                "quantity": 1,
                "repeats": 0
            }]
        }

        response = self.client.post(self.prescription_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["patient"], self.patient.id)
        self.assertIn("download_url", response.data)

    def test_list_prescriptions_as_doctor(self):
        Prescription.objects.create(doctor=self.doctor, patient=self.patient)
        Prescription.objects.create(doctor=self.doctor, patient=self.other_patient)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_list_prescriptions_as_patient(self):
        Prescription.objects.create(doctor=self.doctor, patient=self.patient)
        Prescription.objects.create(doctor=self.doctor, patient=self.other_patient)

        self.client.force_authenticate(user=self.patient)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for rx in response.data["results"]:
            self.assertEqual(rx["patient"], self.patient.id)

    def test_search_prescriptions_by_name(self):
        # Give doctor a name so search works
        self.doctor.first_name = "John"
        self.doctor.last_name = "Doctor"
        self.doctor.save()

        Prescription.objects.create(doctor=self.doctor, patient=self.patient)

        response = self.client.get(f"{self.list_url}?search=doctor")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

        # Look explicitly at doctor_name field
        self.assertTrue(
            any("doctor" in r["doctor_name"].lower() for r in response.data["results"])
        )

    def test_pdf_download_url_format(self):
        pres = Prescription.objects.create(doctor=self.doctor, patient=self.patient)
        response = self.client.get(self.list_url)
        download_url = response.data["results"][0]["download_url"]
        self.assertTrue(download_url.startswith("/api/v1/prescriptions/pdf/"))

    def test_prescription_list_contains_readable_names(self):
        prescription = Prescription.objects.create(doctor=self.doctor, patient=self.patient)

        PrescriptionDrug.objects.create(
            prescription=prescription,
            drug=self.drug,
            dosage="2 tablets",
            instructions="After meals",
            quantity=1,
            repeats=0
        )

        PrescriptionSupplierProduct.objects.create(
            prescription=prescription,
            product=self.product,
            dosage="Apply at night",
            instructions="External use only",
            quantity=1,
            repeats=0
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rx = response.data["results"][0]

        if rx["prescribed_drugs"]:
            drug_entry = rx["prescribed_drugs"][0]
            self.assertIn("drug_name", drug_entry)
            self.assertIn("brand_name", drug_entry)

        if rx["prescribed_supplier_products"]:
            product_entry = rx["prescribed_supplier_products"][0]
            self.assertIn("brand_name", product_entry)
            self.assertIn("generic_name", product_entry)
            self.assertIn("cultivar", product_entry)
