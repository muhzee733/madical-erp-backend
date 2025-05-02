# views.py
from rest_framework.views import APIView
import stripe
from django.conf import settings
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Order
from appointment.models import AppointmentAvailability
from users.permissions import IsPatient
from .serializers import OrderSerializer
from chat.models import ChatRoom

stripe.api_key = settings.STRIPE_SECRET_KEY
# stripe.api_key = settings.STRIPE_WEBHOOK_SECRET

class CreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated, IsPatient]
    def post(self, request):
        try:
            user = request.user 
            appointment_id = request.data.get('appointmentId')

            if not appointment_id:
                return Response({"message": "Appointment ID missing"}, status=status.HTTP_200_OK)
            
            try:
                appointment = AppointmentAvailability.objects.get(id=appointment_id)
            except AppointmentAvailability.DoesNotExist:
                return Response({"message": "Appointment not found."}, status=status.HTTP_200_OK)
            
            if Order.objects.filter(appointment=appointment).exists():
                return Response({"message": "Appointment already booked."}, status=status.HTTP_200_OK)
            
            amount = appointment.price
            appointment_id = appointment.id

            # Prepare order data
            order_data = {
                'amount': amount,
                'status': 'pending'
            }

            # Serialize the order data
            serializer = OrderSerializer(data=order_data)
            
            # Check if serializer is valid and save the order
            if serializer.is_valid():
                order = serializer.save(user=user, appointment=appointment)
                ChatRoom.objects.get_or_create(
                    doctor=appointment.doctor,
                    patient=user,
                    appointment=appointment
                )
                return Response({
                    "message": "Order created successfully.",
                    "orderId": order.id,
                    "status": order.status
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Order creation failed.",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"message": "Error while creating the order.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CreateStripeCheckoutSession(APIView):
    def post(self, request, *args, **kwargs):
        try:
            order_id = request.data.get('orderId')  # Frontend se order id aayegi

            if not order_id:
                return Response({"error": "Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            # Stripe checkout session create
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"Appointment Booking - {order.appointment.doctor.first_name}",  # Customize product name
                        },
                        'unit_amount': int(order.amount * 100),  # Stripe amount is in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='http://localhost:3000/appointment-success?session_id={CHECKOUT_SESSION_ID}',  # Apne frontend ka success page
                cancel_url='http://localhost:3000/cancel',  # Apne frontend ka cancel page
                metadata={
                    'order_id': str(order.id)
                }
            )

            return Response({'checkout_url': session.url})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class OrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            if user.role == 'doctor': 
                orders = Order.objects.filter(appointment_id__doctor=user)
            else:
                orders = Order.objects.filter(user=user)
            if not orders.exists():
                return Response(
                    {"message": "No orders found."},
                    status=status.HTTP_200_OK,
                )
            for order in orders:
                appointment = AppointmentAvailability.objects.get(id=order.appointment.id)
                order.appointment = appointment
                
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        

        except Exception as e:
            return Response({"message": "Error while fetching orders.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
