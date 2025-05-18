from rest_framework import serializers
from .models import Prescription, PrescriptionDrug, Drug

class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'


class PrescriptionDrugWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionDrug
        fields = ['drug', 'dosage', 'instructions', 'quantity', 'repeats']

class PrescriptionSerializer(serializers.ModelSerializer):
    prescribed_drugs = PrescriptionDrugWriteSerializer(many=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'notes', 'created_at', 'signature_image',
            'is_final', 'prescribed_drugs', 'download_url'
        ]
        read_only_fields = ['created_at']

    def get_download_url(self, obj):
        return f"/api/v1/prescriptions/pdf/{obj.id}/"

    def create(self, validated_data):
        prescribed_drugs_data = validated_data.pop('prescribed_drugs')
        prescription = Prescription.objects.create(
            doctor=self.context['request'].user,
            **validated_data
        )
        for item in prescribed_drugs_data:
            PrescriptionDrug.objects.create(prescription=prescription, **item)
        return prescription
