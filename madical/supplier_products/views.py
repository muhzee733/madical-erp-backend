from rest_framework import generics
from .models import SupplierProduct
from .serializers import SupplierProductSerializer

class SupplierProductListView(generics.ListAPIView):
    queryset = SupplierProduct.objects.all()
    serializer_class = SupplierProductSerializer
