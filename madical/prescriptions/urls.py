from django.urls import path
from .views import DrugListCreateView, PrescriptionCreateView, PrescriptionListView

urlpatterns = [
    path('drugs/', DrugListCreateView.as_view(), name='drug-list'),
    path('', PrescriptionCreateView.as_view(), name='prescription-create'),
    path('my/', PrescriptionListView.as_view(), name='my-prescriptions'),
]
