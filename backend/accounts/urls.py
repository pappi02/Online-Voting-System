"""
URL configuration for accounts app
"""

from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from accounts.views import (
    CustomTokenObtainPairView, UserRegistrationView, UserProfileViewSet,
    OTPVerificationView, SendOTPView, UserManagementViewSet,
    RegistrationOTPRequestView, RegistrationOTPVerifyView
)
from accounts.voter_views import (
    VoterRegistrationView, VoterProfileViewSet, VoterDocumentViewSet,
    VerificationManagementViewSet, EligibilityRuleViewSet, VerificationLogViewSet
)
from accounts.security_views import (
    TwoFactorAuthViewSet, TrustedDevicesViewSet, SecurityQuestionsViewSet
)

app_name = 'accounts'

# Create a router for viewsets
router = DefaultRouter()
router.register(r'users/management', UserManagementViewSet, basename='user-management')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'voter/profile', VoterProfileViewSet, basename='voter-profile')
router.register(r'voter/documents', VoterDocumentViewSet, basename='voter-documents')
router.register(r'verification', VerificationManagementViewSet, basename='verification')
router.register(r'eligibility-rules', EligibilityRuleViewSet, basename='eligibility-rules')
router.register(r'verification-logs', VerificationLogViewSet, basename='verification-logs')

# Security endpoints
router.register(r'2fa', TwoFactorAuthViewSet, basename='2fa')
router.register(r'trusted-devices', TrustedDevicesViewSet, basename='trusted-devices')
router.register(r'security-questions', SecurityQuestionsViewSet, basename='security-questions')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/register/request-otp/', RegistrationOTPRequestView.as_view(), name='register-request-otp'),
    path('auth/register/verify-otp/', RegistrationOTPVerifyView.as_view(), name='register-verify-otp'),
    
    # Voter registration
    path('voter/register/', VoterRegistrationView.as_view(), name='voter-register'),
    
    # OTP endpoints
    path('otp/send/', SendOTPView.as_view(), name='send-otp'),
    path('otp/verify/', OTPVerificationView.as_view(), name='verify-otp'),
    
    # Router URLs
    path('', include(router.urls)),
]
