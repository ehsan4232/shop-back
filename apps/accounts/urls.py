from django.urls import path
from . import views

urlpatterns = [
    path('send-otp/', views.SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]