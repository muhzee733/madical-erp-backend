from django.urls import path
from .views import SupplierProductListView, SupplierProductDetailView

urlpatterns = [
    path('', SupplierProductListView.as_view(), name='supplier-product-list'),
    path('<int:pk>/', SupplierProductDetailView.as_view(), name='supplier-product-detail'),
]
