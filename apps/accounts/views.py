from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .models import User, OTPVerification
from .serializers import UserSerializer, OTPVerificationSerializer

class SendOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'شماره تلفن الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or get existing OTP
        otp = OTPVerification.objects.create(phone_number=phone_number)
        
        # TODO: Send SMS here
        # For development, return OTP in response
        return Response({
            'message': 'کد تایید ارسال شد',
            'otp_code': otp.otp_code  # Remove in production
        })

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp_code = request.data.get('otp_code')
        
        try:
            otp = OTPVerification.objects.filter(
                phone_number=phone_number,
                otp_code=otp_code,
                is_verified=False
            ).latest('created_at')
            
            if otp.is_expired():
                return Response({'error': 'کد تایید منقضی شده است'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark OTP as verified
            otp.is_verified = True
            otp.save()
            
            # Create or get user
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'username': phone_number}
            )
            
            return Response({
                'message': 'ورود موفقیت‌آمیز',
                'user': UserSerializer(user).data,
                'created': created
            })
            
        except OTPVerification.DoesNotExist:
            return Response({'error': 'کد تایید نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)