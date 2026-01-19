"""
Serializers for authentication and user management
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from accounts.models import OTPVerification, UserAuditLog
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer with enhanced security
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['status'] = user.status
        token['full_name'] = user.get_full_name()
        
        return token
    
    def validate(self, attrs):
        """Override validation to add security checks"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password')
        
        # Check if account is locked
        if user.is_locked_out():
            raise serializers.ValidationError(
                'Account is locked due to multiple failed login attempts. Try again later.'
            )
        
        # Check if account is active
        if not user.is_active:
            raise serializers.ValidationError('Account is inactive')
        
        # Check if account is approved
        if user.status not in ['approved', 'pending']:
            raise serializers.ValidationError(f'Account status: {user.get_status_display()}')
        
        # Validate password
        if not user.check_password(password):
            user.record_failed_login()
            raise serializers.ValidationError('Invalid email or password')
        
        # Reset login attempts on success
        user.reset_login_attempts()
        
        # Log successful login
        UserAuditLog.objects.create(
            user=user,
            action='login',
            description='User logged in successfully',
        )
        
        attrs['user'] = user
        return super().validate(attrs)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration serializer with validation
    """
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone_number',
            'national_id', 'password', 'password_confirm',
            'institution', 'department'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Validate form data"""
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        
        # Check if email already exists
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Email already registered'})
        
        # Check if national ID already exists
        if data.get('national_id') and User.objects.filter(national_id=data['national_id']).exists():
            raise serializers.ValidationError({'national_id': 'National ID already registered'})
        
        return data
    
    def create(self, validated_data):
        """Create new user"""
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number'),
            national_id=validated_data.get('national_id'),
            institution=validated_data.get('institution'),
            department=validated_data.get('department'),
            role='voter',
            status='pending',
        )
        
        logger.info(f"New user registered: {user.email}")
        
        # Log registration
        UserAuditLog.objects.create(
            user=user,
            action='login',  # Would be different if we had registration action
            description='User account created'
        )
        
        return user


class RegistrationOTPRequestSerializer(serializers.Serializer):
    """Request an OTP for email verification during registration"""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)

        if password != password_confirm:
            raise serializers.ValidationError({'password': 'Passwords do not match'})

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Email already registered'})

        return attrs


class RegistrationOTPVerifySerializer(serializers.Serializer):
    """Verify registration OTP and finalize account creation"""

    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        cache_key = f"registration_otp:{email}"
        cached = cache.get(cache_key)
        if not cached:
            raise serializers.ValidationError({'otp_code': 'OTP has expired or was not requested'})

        attrs['cached'] = cached
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    User profile serializer (read/update)
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_vote = serializers.BooleanField(read_only=True)
    is_locked_out = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'national_id', 'role', 'role_display',
            'status', 'status_display', 'mfa_enabled', 'mfa_method',
            'id_verified', 'has_voted', 'institution', 'department',
            'can_vote', 'is_locked_out', 'last_login', 'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'status', 'id_verified', 'has_voted',
            'national_id', 'last_login', 'created_at', 'updated_at'
        ]
    
    def get_is_locked_out(self, obj):
        """Check if user account is locked"""
        return obj.is_locked_out()
    
    def update(self, instance, validated_data):
        """Update user profile"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        logger.info(f"User profile updated: {instance.email}")
        
        # Log profile update
        UserAuditLog.objects.create(
            user=instance,
            action='profile_updated',
            description='User profile was updated',
            details=validated_data
        )
        
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """
    Change password serializer
    """
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect')
        return value
    
    def validate_new_password(self, value):
        """Validate new password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Validate form data"""
        if data['new_password'] != data.pop('new_password_confirm'):
            raise serializers.ValidationError({'new_password': 'Passwords do not match'})
        
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({'new_password': 'New password must differ from old password'})
        
        return data
    
    def save(self):
        """Save new password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.update_password_change_time()
        
        logger.info(f"Password changed: {user.email}")
        
        # Log password change
        UserAuditLog.objects.create(
            user=user,
            action='password_change',
            description='User password was changed'
        )
        
        return user


class OTPSerializer(serializers.ModelSerializer):
    """
    OTP verification serializer
    """
    otp_code = serializers.CharField(max_length=6, write_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = OTPVerification
        fields = ['id', 'otp_code', 'method', 'purpose', 'contact_info', 
                  'created_at', 'expires_at', 'is_valid', 'attempts']
        read_only_fields = ['id', 'method', 'purpose', 'contact_info', 
                            'created_at', 'expires_at', 'attempts']
    
    def get_is_valid(self, obj):
        """Check if OTP is still valid"""
        return obj.is_valid()
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError('OTP must be a 6-digit number')
        return value


class OTPRequestSerializer(serializers.Serializer):
    """
    OTP request serializer for generating new OTP
    """
    method = serializers.ChoiceField(choices=['sms', 'email'], default='email')
    purpose = serializers.ChoiceField(
        choices=['login', 'registration', 'password_reset', 'account_recovery'],
        default='login'
    )


class ResendOTPSerializer(serializers.Serializer):
    """
    Resend OTP serializer
    """
    email = serializers.EmailField()
    method = serializers.ChoiceField(choices=['sms', 'email'])
    purpose = serializers.ChoiceField(
        choices=['login', 'registration', 'password_reset', 'account_recovery']
    )
    
    def validate_email(self, value):
        """Validate email exists"""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Email not found')
        return value


class PasswordResetSerializer(serializers.Serializer):
    """
    Password reset serializer
    """
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate email exists"""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Email not found')
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Password reset confirmation serializer
    """
    token = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_new_password(self, value):
        """Validate new password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Validate form data"""
        if data['new_password'] != data.pop('new_password_confirm'):
            raise serializers.ValidationError({'new_password': 'Passwords do not match'})
        return data
