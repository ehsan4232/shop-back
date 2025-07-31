from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.accounts.serializers import UserSerializer, UserProfileSerializer
from apps.tenants.models import Tenant
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user info"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to token response
        user_serializer = UserSerializer(self.user)
        data['user'] = user_serializer.data
        
        # Add tenant information if available
        if hasattr(self.user, 'tenant'):
            data['tenant'] = {
                'id': self.user.tenant.id,
                'name': self.user.tenant.name,
                'domain': self.user.tenant.domain,
            }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view"""
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            logger.info(f"User {request.data.get('email', 'unknown')} logged in successfully")
            return response
        except Exception as e:
            logger.warning(f"Login attempt failed for {request.data.get('email', 'unknown')}: {str(e)}")
            raise


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """User registration endpoint"""
    try:
        data = request.data
        
        # Required fields validation
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {'error': f'{field} is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if user already exists
        if User.objects.filter(email=data['email']).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate password
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response(
                {'error': e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create tenant based on domain
        tenant_domain = data.get('tenant_domain', 'default')
        tenant, created = Tenant.objects.get_or_create(
            domain=tenant_domain,
            defaults={
                'name': tenant_domain.title(),
                'is_active': True
            }
        )
        
        # Create user
        user = User.objects.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            tenant=tenant
        )
        
        # Create user profile if additional data provided
        profile_data = {
            'phone': data.get('phone', ''),
            'date_of_birth': data.get('date_of_birth'),
            'gender': data.get('gender'),
            'address': data.get('address', ''),
            'city': data.get('city', ''),
            'state': data.get('state', ''),
            'zip_code': data.get('zip_code', ''),
            'country': data.get('country', 'US'),
        }
        
        # Update profile with provided data
        for key, value in profile_data.items():
            if value:
                setattr(user.profile, key, value)
        user.profile.save()
        
        # Generate tokens
        serializer = CustomTokenObtainPairSerializer()
        tokens = serializer.get_token(user)
        
        logger.info(f"New user registered: {user.email}")
        
        return Response({
            'message': 'User registered successfully',
            'access': str(tokens.access_token),
            'refresh': str(tokens),
            'user': UserSerializer(user).data,
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'domain': tenant.domain,
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response(
            {'error': 'Registration failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Get current user profile"""
    try:
        user_serializer = UserSerializer(request.user)
        profile_serializer = UserProfileSerializer(request.user.profile)
        
        return Response({
            'user': user_serializer.data,
            'profile': profile_serializer.data,
        })
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return Response(
            {'error': 'Failed to fetch profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """Update current user profile"""
    try:
        user = request.user
        data = request.data
        
        # Update user fields
        user_fields = ['first_name', 'last_name', 'email']
        for field in user_fields:
            if field in data:
                if field == 'email' and data[field] != user.email:
                    # Check if email is already taken
                    if User.objects.filter(email=data[field]).exclude(id=user.id).exists():
                        return Response(
                            {'error': 'Email already in use'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                setattr(user, field, data[field])
        
        user.save()
        
        # Update profile fields
        profile_fields = [
            'phone', 'date_of_birth', 'gender', 'address', 
            'city', 'state', 'zip_code', 'country', 'bio'
        ]
        
        for field in profile_fields:
            if field in data:
                setattr(user.profile, field, data[field])
        
        user.profile.save()
        
        logger.info(f"User profile updated: {user.email}")
        
        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(user.profile).data,
        })
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return Response(
            {'error': 'Failed to update profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    try:
        user = request.user
        data = request.data
        
        # Validate current password
        if not user.check_password(data.get('current_password')):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new password
        new_password = data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'New password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {'error': e.messages},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Confirm password match
        if new_password != data.get('confirm_password'):
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return Response({
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return Response(
            {'error': 'Failed to change password'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user (blacklist refresh token)"""
    try:
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import here to avoid circular imports
        from rest_framework_simplejwt.tokens import RefreshToken
        
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        logger.info(f"User logged out: {request.user.email}")
        
        return Response({
            'message': 'Logged out successfully'
        })
        
    except TokenError:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token(request):
    """Verify if token is valid"""
    try:
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import here to avoid circular imports
        from rest_framework_simplejwt.tokens import AccessToken
        
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        
        return Response({
            'valid': True,
            'user': UserSerializer(user).data
        })
        
    except (TokenError, User.DoesNotExist):
        return Response({
            'valid': False,
            'error': 'Invalid token'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return Response(
            {'error': 'Token verification failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )