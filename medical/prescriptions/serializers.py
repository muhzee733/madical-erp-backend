from rest_framework import serializers
from .models import Prescription, PrescriptionDrug, PrescriptionSupplierProduct, Drug
from supplier_products.models import SupplierProduct


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = '__all__'


class SupplierProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierProduct
        fields = '__all__'


class PrescriptionDrugWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionDrug
        fields = ['drug', 'dosage', 'instructions', 'quantity', 'repeats']


class PrescriptionSupplierProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionSupplierProduct
        fields = ['product', 'dosage', 'instructions', 'quantity', 'repeats']


class PrescriptionSerializer(serializers.ModelSerializer):
    prescribed_drugs = PrescriptionDrugWriteSerializer(many=True)
    prescribed_supplier_products = PrescriptionSupplierProductWriteSerializer(many=True)
    download_url = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'notes', 'created_at', 'signature_image',
            'is_final', 'prescribed_drugs', 'prescribed_supplier_products',
            'download_url', 'doctor_name'
        ]
        read_only_fields = ['created_at']

    def get_download_url(self, obj):
        return f"/api/v1/prescriptions/pdf/{obj.id}/"
    
    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}".strip()


    def create(self, validated_data):
        prescribed_drugs_data = validated_data.pop('prescribed_drugs', [])
        prescribed_supplier_products_data = validated_data.pop('prescribed_supplier_products', [])

        prescription = Prescription.objects.create(
            doctor=self.context['request'].user,
            **validated_data
        )

        for item in prescribed_drugs_data:
            PrescriptionDrug.objects.create(prescription=prescription, **item)

        for item in prescribed_supplier_products_data:
            PrescriptionSupplierProduct.objects.create(prescription=prescription, **item)

        return prescription

class PrescriptionDrugReadSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.name', read_only=True)

    class Meta:
        model = PrescriptionDrug
        fields = ['drug', 'drug_name', 'dosage', 'instructions', 'quantity', 'repeats']

class PrescriptionSupplierProductReadSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = PrescriptionSupplierProduct
        fields = ['product', 'product_name', 'dosage', 'instructions', 'quantity', 'repeats']

class PrescriptionListSerializer(serializers.ModelSerializer):
    prescribed_drugs = PrescriptionDrugReadSerializer(many=True, read_only=True)
    prescribed_supplier_products = PrescriptionSupplierProductReadSerializer(many=True, read_only=True)
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'patient_name', 'notes', 'created_at', 'signature_image',
            'is_final', 'prescribed_drugs', 'prescribed_supplier_products',
            'download_url', 'doctor_name'
        ]

    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}".strip()

    def get_download_url(self, obj):
        return f"/api/v1/prescriptions/pdf/{obj.id}/"
