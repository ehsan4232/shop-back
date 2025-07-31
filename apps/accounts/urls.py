from django.urls import path
from .views import (
    send_otp, 
    verify_otp, 
    logout, 
    profile, 
    update_profile,
    user_sessions,
    revoke_session,
    CustomTokenRefreshView
)
from .otp_views import (
    send_otp as send_otp_new,
    verify_otp as verify_otp_new,
    resend_otp,
    check_phone_exists
)
from .auth_views import (
    request_otp,
    verify_otp as auth_verify_otp,
    complete_store_owner_profile,
    logout as auth_logout
)

app_name = 'accounts'

urlpatterns = [
    # OTP Authentication (NEW - Product Description Requirement)
    path('send-otp/', send_otp_new, name='send_otp_new'),
    path('verify-otp/', verify_otp_new, name='verify_otp_new'),
    path('resend-otp/', resend_otp, name='resend_otp'),
    path('check-phone/', check_phone_exists, name='check_phone_exists'),
    
    # Enhanced OTP Auth (from auth_views.py)
    path('auth/request-otp/', request_otp, name='request_otp'),
    path('auth/verify-otp/', auth_verify_otp, name='auth_verify_otp'),
    path('auth/complete-profile/', complete_store_owner_profile, name='complete_profile'),
    path('auth/logout/', auth_logout, name='auth_logout'),
    
    # Legacy Authentication (keeping for backward compatibility)
    path('auth/send-otp/', send_otp, name='send_otp_legacy'),
    path('auth/verify-otp/', verify_otp, name='verify_otp_legacy'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', logout, name='logout'),
    
    # Profile management
    path('profile/', profile, name='profile'),
    path('profile/update/', update_profile, name='update_profile'),
    
    # Session management
    path('sessions/', user_sessions, name='user_sessions'),
    path('sessions/revoke/', revoke_session, name='revoke_session'),
]