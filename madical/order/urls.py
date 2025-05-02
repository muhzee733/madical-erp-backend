from django.urls import path
from .views import CreateOrderAPIView, CreateStripeCheckoutSession, OrderListAPIView

urlpatterns = [
    path('create_order/', CreateOrderAPIView.as_view(), name='create-order'),
    path('create-stripe-session/', CreateStripeCheckoutSession.as_view(), name='stripe_session'),
    path('orders/', OrderListAPIView.as_view(), name='order-list')
]