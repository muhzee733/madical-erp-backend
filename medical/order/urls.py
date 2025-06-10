from django.urls import path
from .views import CreateOrderAPIView, CreateStripeCheckoutSession, OrderListAPIView, stripe_webhook, StripeSessionSuccessAPIView

urlpatterns = [
    path('create_order/', CreateOrderAPIView.as_view(), name='create-order'),
    path('create-stripe-session/', CreateStripeCheckoutSession.as_view(), name='stripe_session'),
    path('', OrderListAPIView.as_view(), name='order-list'),
    path('stripe-webhook/', stripe_webhook),
    path('payment/success', StripeSessionSuccessAPIView.as_view(), name='stripe-success'),
]