from rest_framework import generics, permissions
from .models import SupplierProduct
from .serializers import SupplierProductSerializer

class SupplierProductDetailView(generics.RetrieveAPIView):
    queryset = SupplierProduct.objects.all()
    serializer_class = SupplierProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class SupplierProductListView(generics.ListAPIView):
    queryset = SupplierProduct.objects.all().order_by('id')
    serializer_class = SupplierProductSerializer
    permission_classes = [permissions.IsAuthenticated]
