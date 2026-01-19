"""
Authentication and user management views
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from accounts.serializers import (
    CustomTokenObtainPairSerializer, UserRegistrationSerializer,
    UserProfileSerializer, ChangePasswordSerializer, OTPSerializer,
    OTPRequestSerializer, ResendOTPSerializer,
    RegistrationOTPRequestSerializer, RegistrationOTPVerifySerializer
)
from accounts.models import OTPVerification, UserAuditLog
from accounts.permissions import IsAdmin
from accounts.utils import (
    create_otp_for_user, send_otp_email, send_otp_sms,
    verify_otp, get_client_ip, get_user_agent, log_audit_event,
    check_rate_limit, generate_otp_code
)
import logging
import secrets
import string

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Enhanced login endpoint with security checks
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        """Handle user creation"""
        user = serializer.save()
        logger.info(f"New user registered: {user.email}")
        
        # Send verification email
        self.send_verification_email(user)
    
    def send_verification_email(self, user):
        """Send email verification link"""
        try:
            subject = 'Verify Your iVote Systems Account'
            message = f'''
            Hello {user.first_name},
            
            Welcome to iVote Systems! Please verify your email address to complete registration.
            
            Your account is currently pending approval from administrators.
            
            Click the link below to confirm your email:
            [Verification Link would be sent here]
            
            Best regards,
            iVote Systems Team
            '''
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")


class RegistrationOTPRequestView(generics.CreateAPIView):
    """Request an OTP for registration (unauthenticated)"""

    serializer_class = RegistrationOTPRequestSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data['last_name']
        password = serializer.validated_data['password']

        otp_code = generate_otp_code()
        cache_key = f"registration_otp:{email}"
        cache.set(
            cache_key,
            {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password,
                'otp_code': otp_code,
            },
            timeout=300  # 5 minutes
        )

        try:
            subject = 'iVote Systems - Complete Your Registration'
            message = (
                f"Hello {first_name},\n\n"
                f"Your iVote Systems verification code is: {otp_code}\n\n"
                "This code expires in 5 minutes. If you did not request this, please ignore this email.\n\n"
                "iVote Systems Team"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            logger.info(f"Registration OTP sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send registration OTP to {email}: {str(e)}")
            cache.delete(cache_key)
            return Response(
                {'error': 'Failed to send verification email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                'message': 'Verification code sent to your email. Valid for 5 minutes.',
                'expires_in': 300
            },
            status=status.HTTP_200_OK
        )


class RegistrationOTPVerifyView(generics.CreateAPIView):
    """Verify registration OTP and create the user"""

    serializer_class = RegistrationOTPVerifySerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        cached = serializer.validated_data['cached']
        cache_key = f"registration_otp:{email}"

        if cached['otp_code'] != otp_code:
            return Response(
                {'error': 'Invalid verification code.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user now that email is verified
        user = User.objects.create_user(
            email=cached['email'],
            password=cached['password'],
            first_name=cached['first_name'],
            last_name=cached['last_name'],
            role='voter',
            status='approved'
        )

        # Cleanup cache
        cache.delete(cache_key)

        # Log registration
        UserAuditLog.objects.create(
            user=user,
            action='login',
            description='User registered via email OTP verification'
        )

        return Response(
            {
                'message': 'Email verified and account created successfully.',
                'user_id': user.id
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileViewSet(viewsets.ViewSet):
    """
    User profile management viewset
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Password changed successfully'},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def enable_mfa(self, request):
        """Enable multi-factor authentication"""
        method = request.data.get('method')
        
        if method not in ['sms', 'email', 'authenticator']:
            return Response(
                {'error': 'Invalid MFA method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        user.mfa_method = method
        user.save()
        
        logger.info(f"MFA enabled for {user.email} with method {method}")
        
        # Log MFA enablement
        UserAuditLog.objects.create(
            user=user,
            action='mfa_enabled',
            description=f'MFA enabled with method: {method}'
        )
        
        return Response(
            {'message': f'MFA enabled via {method}'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def disable_mfa(self, request):
        """Disable multi-factor authentication"""
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user.mfa_enabled = False
        user.mfa_method = None
        user.save()
        
        logger.info(f"MFA disabled for {user.email}")
        
        # Log MFA disablement
        UserAuditLog.objects.create(
            user=user,
            action='mfa_disabled',
            description='MFA was disabled'
        )
        
        return Response(
            {'message': 'MFA disabled'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def audit_logs(self, request):
        """Get user's audit logs"""
        logs = UserAuditLog.objects.filter(user=request.user).order_by('-timestamp')[:20]
        data = [
            {
                'action': log.get_action_display(),
                'timestamp': log.timestamp,
                'description': log.description,
                'ip_address': log.ip_address
            }
            for log in logs
        ]
        return Response(data)


class OTPVerificationView(generics.CreateAPIView):
    """
    OTP verification endpoint
    """
    serializer_class = OTPSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Verify OTP"""
        otp_code = request.data.get('otp_code')
        purpose = request.data.get('purpose', 'login')
        
        # Verify OTP using utility function
        success, message = verify_otp(request.user, otp_code, purpose)
        
        if success:
            # Log OTP verification
            log_audit_event(
                user=request.user,
                action='login',
                description=f'OTP verified for {purpose}',
                request=request
            )
            
            return Response(
                {'message': message},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )


class SendOTPView(generics.CreateAPIView):
    """
    Send OTP for verification
    """
    serializer_class = OTPRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Send OTP to user"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        method = serializer.validated_data.get('method', 'email')
        purpose = serializer.validated_data.get('purpose', 'login')
        user = request.user
        
        # Check rate limit (max 5 OTP requests per 15 minutes)
        allowed, remaining, reset_time = check_rate_limit(
            user, 
            action='otp_request',
            max_attempts=5,
            window_minutes=15
        )
        
        if not allowed:
            return Response(
                {
                    'error': 'Too many OTP requests. Please try again later.',
                    'reset_time': reset_time
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Create OTP
        otp = create_otp_for_user(user, purpose=purpose, method=method)
        
        # Send OTP via chosen method
        if method == 'email':
            success = send_otp_email(user, otp.otp_code, purpose)
        else:
            success = send_otp_sms(user, otp.otp_code, purpose)
        
        if not success:
            return Response(
                {'error': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Log OTP request
        log_audit_event(
            user=user,
            action='login',
            description=f'OTP requested via {method} for {purpose}',
            request=request,
            details={'method': method, 'purpose': purpose}
        )
        
        return Response(
            {
                'message': f'OTP sent successfully via {method}',
                'expires_at': otp.expires_at,
                'remaining_requests': remaining - 1
            },
            status=status.HTTP_200_OK
        )
        """Generate and send OTP"""
        method = request.data.get('method', 'email')
        purpose = request.data.get('purpose', 'login')
        user = request.user
        
        if method not in ['sms', 'email']:
            return Response(
                {'error': 'Invalid OTP method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate 6-digit OTP
        otp_code = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Determine contact info
        if method == 'sms':
            if not user.phone_number:
                return Response(
                    {'error': 'Phone number not configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            contact_info = user.phone_number
        else:
            contact_info = user.email
        
        # Create OTP record
        otp_expires = timezone.now() + timezone.timedelta(minutes=10)
        otp = OTPVerification.objects.create(
            user=user,
            otp_code=otp_code,
            method=method,
            purpose=purpose,
            contact_info=contact_info,
            expires_at=otp_expires
        )
        
        # Send OTP
        if method == 'email':
            self.send_otp_email(user, otp_code)
        else:
            self.send_otp_sms(user, otp_code)
        
        logger.info(f"OTP sent to {user.email} via {method}")
        
        return Response(
            {
                'message': f'OTP sent to {contact_info}',
                'expires_in': 600  # 10 minutes in seconds
            },
            status=status.HTTP_200_OK
        )
    
    def send_otp_email(self, user, otp_code):
        """Send OTP via email"""
        try:
            subject = 'Your iVote Systems Verification Code'
            message = f'''
            Your verification code is: {otp_code}
            
            This code expires in 10 minutes.
            
            If you did not request this code, please ignore this email.
            
            iVote Systems Team
            '''
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception as e:
            logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
    
    def send_otp_sms(self, user, otp_code):
        """Send OTP via SMS (requires Twilio configuration)"""
        try:
            from twilio.rest import Client
            
            if not all([
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
                settings.TWILIO_PHONE_NUMBER
            ]):
                logger.warning("Twilio not configured for SMS")
                return
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=f'Your iVote Systems verification code is: {otp_code}. Valid for 10 minutes.',
                from_=settings.TWILIO_PHONE_NUMBER,
                to=user.phone_number
            )
            logger.info(f"SMS OTP sent to {user.phone_number}")
        except Exception as e:
            logger.error(f"Failed to send OTP SMS to {user.phone_number}: {str(e)}")


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    Admin user management viewset
    """
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdmin]
    filter_fields = ['role', 'status']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'email']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve pending user"""
        user = self.get_object()
        if user.status != 'pending':
            return Response(
                {'error': 'Only pending users can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.status = 'approved'
        user.save()
        
        logger.info(f"User approved: {user.email}")
        
        # Log status change
        UserAuditLog.objects.create(
            user=user,
            action='status_changed',
            description='User status changed to approved'
        )
        
        # Send approval email
        self.send_approval_email(user)
        
        return Response({'message': 'User approved'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject pending user"""
        user = self.get_object()
        reason = request.data.get('reason', '')
        
        user.status = 'rejected'
        user.save()
        
        logger.info(f"User rejected: {user.email}")
        
        # Log status change
        UserAuditLog.objects.create(
            user=user,
            action='status_changed',
            description=f'User status changed to rejected. Reason: {reason}'
        )
        
        return Response({'message': 'User rejected'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block user"""
        user = self.get_object()
        reason = request.data.get('reason', '')
        
        user.status = 'blocked'
        user.is_active = False
        user.save()
        
        logger.warning(f"User blocked: {user.email}")
        
        # Log status change
        UserAuditLog.objects.create(
            user=user,
            action='status_changed',
            description=f'User account blocked. Reason: {reason}'
        )
        
        return Response({'message': 'User blocked'}, status=status.HTTP_200_OK)
    
    def send_approval_email(self, user):
        """Send approval email"""
        try:
            subject = 'Welcome to iVote Systems - Account Approved'
            message = f'''
            Hello {user.first_name},
            
            Your iVote Systems account has been approved!
            
            You can now log in and participate in elections.
            
            Best regards,
            iVote Systems Team
            '''
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception as e:
            logger.error(f"Failed to send approval email to {user.email}: {str(e)}")
