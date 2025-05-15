from django.urls import path
from .views import (
    DrugListCreateView,
    PrescriptionCreateView,
    PrescriptionListView,
    download_prescription_pdf
)

urlpatterns = [
    path('drugs/', DrugListCreateView.as_view(), name='drug-list-create'),
    path('', PrescriptionCreateView.as_view(), name='prescription-create'), 
    path('list/', PrescriptionListView.as_view(), name='prescription-list'),
    path('pdf/<int:prescription_id>/', download_prescription_pdf, name='prescription-pdf'),
]
