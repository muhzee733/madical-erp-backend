from rest_framework import serializers
from .models import SupplierProduct

class SupplierProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierProduct
        fields = '__all__'
