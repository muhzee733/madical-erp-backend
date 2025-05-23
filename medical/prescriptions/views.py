from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics, permissions, filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import Drug, Prescription
from .serializers import DrugSerializer, PrescriptionSerializer
from .utils.pdf_utils import generate_prescription_pdf
from users.permissions import IsDoctor, IsDoctorOrAdmin


# --------------------
# DRF API Views
# --------------------

class DrugListCreateView(generics.ListCreateAPIView):
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctorOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['pbs_code', 'drug_name', 'brand_name', 'form', 'strength']
    filterset_fields = [
        'form',                     
        'strength',                
        'schedule_code',           
        'program_code',             
        'manufacturer_code',       
        'unit_of_measure',          
        'electronic_chart_eligible',
        'infusible_indicator',     
        'is_active',               
    ]



class PrescriptionCreateView(generics.CreateAPIView):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]


class PrescriptionListView(generics.ListAPIView):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['doctor', 'patient', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__email']

    def get_queryset(self):
        user = self.request.user

        if user.role == 'admin':
            queryset = Prescription.objects.all()
        elif user.role == 'doctor':
            queryset = Prescription.objects.filter(doctor=user)
        elif user.role == 'patient':
            queryset = Prescription.objects.filter(patient=user)
        else:
            return Prescription.objects.none()

        # Optional: custom search override for full name matching
        search = self.request.query_params.get('search')
        if search:
            name_parts = search.strip().split()
            if len(name_parts) >= 2:
                queryset = queryset.filter(
                    Q(patient__first_name__icontains=name_parts[0]) &
                    Q(patient__last_name__icontains=name_parts[1])
                )
            else:
                queryset = queryset.filter(
                    Q(patient__first_name__icontains=search) |
                    Q(patient__last_name__icontains=search) |
                    Q(patient__email__icontains=search)
                )

        return queryset


# --------------------
# PDF Export View
# --------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_prescription_pdf(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)

    # Only the doctor who created it or an admin can access
    if request.user != prescription.doctor and not request.user.is_superuser:
        return Response({"detail": "Unauthorized access"}, status=401)

    pdf_content = generate_prescription_pdf(prescription)

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription_id}.pdf"'
    return response
