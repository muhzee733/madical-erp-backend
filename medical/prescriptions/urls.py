from django.urls import path
from .views import (
    PrescriptionCreateView,
    PrescriptionListView,
    download_prescription_pdf,
)

urlpatterns = [
    path('', PrescriptionCreateView.as_view(), name='prescription-create'), 
    path('list/', PrescriptionListView.as_view(), name='prescription-list'),
    path('pdf/<int:prescription_id>/', download_prescription_pdf, name='prescription-pdf'),
]
