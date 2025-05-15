from rest_framework import serializers
from .models import Drug, Prescription, PrescriptionDrug

class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'

class PrescriptionDrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionDrug
        fields = '__all__'

class PrescriptionSerializer(serializers.ModelSerializer):
    prescribed_drugs = PrescriptionDrugSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = '__all__'
