from rest_framework import serializers
from .models import Prescription, PrescriptionDrug, Drug

class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'


class PrescriptionDrugSerializer(serializers.ModelSerializer):
    drug = DrugSerializer(read_only=True)

    class Meta:
        model = PrescriptionDrug
        fields = ['drug', 'dosage', 'instructions', 'quantity', 'repeats']


class PrescriptionSerializer(serializers.ModelSerializer):
    prescribed_drugs = PrescriptionDrugSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'doctor', 'patient', 'created_at', 'notes',
            'prescribed_drugs', 'download_url'
        ]

    def get_download_url(self, obj):
        return f"/prescriptions/pdf/{obj.id}/"
