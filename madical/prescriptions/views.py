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
from users.permissions import IsDoctor


# --------------------
# DRF API Views
# --------------------

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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__email']

    def get_queryset(self):
        user = self.request.user
        queryset = Prescription.objects.all()

        if user.role == 'doctor':
            queryset = queryset.filter(doctor=user)
        elif user.role == 'patient':
            queryset = queryset.filter(patient=user)
        else:
            return Prescription.objects.none()

        search = self.request.query_params.get('search')
        if search:
            name_parts = search.split()
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

    # Only doctor who created it or admin can access
    if request.user != prescription.doctor and not request.user.is_superuser:
        return Response({"detail": "Unauthorized access"}, status=401)

    pdf_content = generate_prescription_pdf(prescription)

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription_id}.pdf"'
    return response
