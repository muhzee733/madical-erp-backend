from django.urls import path
from .views import SupplierProductListView

urlpatterns = [
    path('', SupplierProductListView.as_view(), name='supplier-product-list'),
]
