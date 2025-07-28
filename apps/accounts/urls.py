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

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('auth/send-otp/', send_otp, name='send_otp'),
    path('auth/verify-otp/', verify_otp, name='verify_otp'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', logout, name='logout'),
    
    # Profile management
    path('profile/', profile, name='profile'),
    path('profile/update/', update_profile, name='update_profile'),
    
    # Session management
    path('sessions/', user_sessions, name='user_sessions'),
    path('sessions/revoke/', revoke_session, name='revoke_session'),
]
