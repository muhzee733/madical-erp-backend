from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Drug, Prescription
from .serializers import DrugSerializer, PrescriptionSerializer
from .utils.pdf_utils import generate_prescription_pdf
from users.permissions import IsDoctor


# --------------------
# DRF API Views
# --------------------

from rest_framework import generics, permissions, filters

class DrugListCreateView(generics.ListCreateAPIView):
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]


class PrescriptionCreateView(generics.CreateAPIView):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]


class PrescriptionListView(generics.ListAPIView):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'doctor':
            return Prescription.objects.filter(doctor=user)
        elif user.role == 'patient':
            return Prescription.objects.filter(patient=user)
        return Prescription.objects.none()


class DrugSearchView(generics.ListAPIView):
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    filter_backends = [filters.SearchFilter]
    search_fields = ['pbs_code', 'drug_name', 'brand_name', 'form', 'strength']

# --------------------
# PDF Export View
# --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_prescription_pdf(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Only doctor who created it or admin can access
    if request.user != prescription.doctor and not request.user.is_superuser:
        return Response({"detail": "Unauthorized access"}, status=401)

    pdf_content = generate_prescription_pdf(prescription)

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription_id}.pdf"'
    return response
