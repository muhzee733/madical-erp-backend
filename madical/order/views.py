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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = 'whsec_RYQRvalTOecFccc9gtYSmV3GUntjYAQY'

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    print(endpoint_secret, 'ss')
    
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({'status': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'status': 'Invalid signature'}, status=400)
    print("Webhook received", event)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session['metadata'].get('order_id')
        payment_intent = session.get('payment_intent')

        try:
            order = Order.objects.get(id=order_id)
            order.status = 'paid'
            order.payment_intent = payment_intent
            order.save()
        except Order.DoesNotExist:
            pass  # Optionally log this

    return JsonResponse({'status': 'success'}, status=200)

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
                success_url = 'http://madical-erp-s3.s3-website.eu-north-1.amazonaws.com/appointment-success?session_id={CHECKOUT_SESSION_ID}',
                
                cancel_url='http://localhost:3000/cancel',  # Apne frontend ka cancel page
                metadata={
                    'order_id': str(order.id)
                }
            )
            order.stripe_session_id = session.id
            order.payment_intent = session.payment_intent
            order.save()
      

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

class StripeSessionSuccessAPIView(APIView):
    def get(self, request):
        session_id = request.GET.get('session_id')

        if not session_id:
            return Response({'error': 'Missing session_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get session and payment info from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            order = Order.objects.get(stripe_session_id=session.id)

            appointment = order.appointment

            return Response({
                'amount': str(order.amount),
                'name': order.user.first_name + ' ' + order.user.last_name,
                'contact': order.user.email, 
                'details': [
                    {
                        'title': f'Appointment with {appointment.doctor.first_name}',
                        'date': f' {appointment.date}',
                        'start_time': f' {appointment.start_time}',
                        'amount': str(order.amount)
                    }
                ]
            }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)