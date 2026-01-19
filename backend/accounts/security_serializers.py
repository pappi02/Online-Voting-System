"""
Two-Factor Authentication Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .security_models import TwoFactorAuth, SecurityQuestion, TrustedDevice

User = get_user_model()


class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for initiating 2FA setup"""
    
    def create(self, validated_data):
        """Generate secret key and QR code"""
        user = self.context['request'].user
        
        # Get or create 2FA instance
        two_factor, created = TwoFactorAuth.objects.get_or_create(
            user=user,
            defaults={'secret_key': TwoFactorAuth.generate_secret_key()}
        )
        
        if not created and two_factor.is_enabled:
            raise serializers.ValidationError("2FA is already enabled")
        
        # Generate new secret if not created
        if not created:
            two_factor.secret_key = TwoFactorAuth.generate_secret_key()
            two_factor.save()
        
        return {
            'secret_key': two_factor.secret_key,
            'qr_code': two_factor.generate_qr_code(),
            'manual_entry_key': two_factor.secret_key
        }


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for verifying 2FA setup"""
    token = serializers.CharField(min_length=6, max_length=6)
    trust_device = serializers.BooleanField(default=False)
    
    def validate_token(self, value):
        """Validate token format"""
        if not value.isdigit():
            raise serializers.ValidationError("Token must be 6 digits")
        return value
    
    def create(self, validated_data):
        """Verify token and enable 2FA"""
        user = self.context['request'].user
        token = validated_data['token']
        trust_device = validated_data.get('trust_device', False)
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=user)
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError("2FA not set up. Please initiate setup first.")
        
        # Verify token
        if not two_factor.verify_token(token):
            # Log failed attempt
            from .security_models import TwoFactorAuthLog
            TwoFactorAuthLog.log_action(
                user=user,
                action='token_failed',
                success=False,
                ip_address=self.context['request'].META.get('REMOTE_ADDR'),
                user_agent=self.context['request'].META.get('HTTP_USER_AGENT', '')
            )
            raise serializers.ValidationError("Invalid token")
        
        # Enable 2FA
        two_factor.enable()
        
        # Generate backup codes
        backup_codes = two_factor.generate_backup_codes()
        
        # Log success
        from .security_models import TwoFactorAuthLog
        TwoFactorAuthLog.log_action(
            user=user,
            action='enabled',
            success=True,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get('HTTP_USER_AGENT', '')
        )
        
        # Trust device if requested
        device_id = None
        if trust_device:
            import hashlib
            request = self.context['request']
            device_string = f"{request.META.get('REMOTE_ADDR')}_{request.META.get('HTTP_USER_AGENT', '')}"
            device_id = hashlib.sha256(device_string.encode()).hexdigest()
            
            TrustedDevice.create_trusted_device(
                user=user,
                device_id=device_id,
                device_name=f"Device from {request.META.get('REMOTE_ADDR')}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return {
            'success': True,
            'message': '2FA enabled successfully',
            'backup_codes': backup_codes,
            'device_id': device_id
        }


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer for disabling 2FA"""
    password = serializers.CharField(write_only=True)
    token = serializers.CharField(min_length=6, max_length=6, required=False)
    
    def validate(self, data):
        """Validate password and optionally token"""
        user = self.context['request'].user
        
        # Check password
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid password")
        
        # If 2FA is enabled, require token
        try:
            two_factor = TwoFactorAuth.objects.get(user=user, is_enabled=True)
            if 'token' not in data:
                raise serializers.ValidationError("Token required to disable 2FA")
            
            if not two_factor.verify_token(data['token']):
                raise serializers.ValidationError("Invalid token")
        except TwoFactorAuth.DoesNotExist:
            pass
        
        return data
    
    def create(self, validated_data):
        """Disable 2FA"""
        user = self.context['request'].user
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=user)
            two_factor.disable()
            
            # Log action
            from .security_models import TwoFactorAuthLog
            TwoFactorAuthLog.log_action(
                user=user,
                action='disabled',
                success=True,
                ip_address=self.context['request'].META.get('REMOTE_ADDR'),
                user_agent=self.context['request'].META.get('HTTP_USER_AGENT', '')
            )
            
            return {'success': True, 'message': '2FA disabled successfully'}
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError("2FA not enabled")


class TwoFactorLoginSerializer(serializers.Serializer):
    """Serializer for 2FA login verification"""
    token = serializers.CharField(min_length=6, max_length=8, required=False)
    backup_code = serializers.CharField(max_length=10, required=False)
    trust_device = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate that either token or backup code is provided"""
        if not data.get('token') and not data.get('backup_code'):
            raise serializers.ValidationError("Either token or backup code required")
        return data
    
    def verify(self, user):
        """Verify 2FA for login"""
        try:
            two_factor = TwoFactorAuth.objects.get(user=user, is_enabled=True)
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError("2FA not enabled")
        
        token = self.validated_data.get('token')
        backup_code = self.validated_data.get('backup_code')
        trust_device = self.validated_data.get('trust_device', False)
        
        verified = False
        method = None
        
        # Try token first
        if token:
            verified = two_factor.verify_token(token)
            method = 'token'
            action = 'token_verified' if verified else 'token_failed'
        
        # Try backup code if token failed or not provided
        if not verified and backup_code:
            verified = two_factor.verify_backup_code(backup_code)
            method = 'backup_code'
            action = 'backup_used' if verified else 'backup_failed'
        
        # Log attempt
        from .security_models import TwoFactorAuthLog
        TwoFactorAuthLog.log_action(
            user=user,
            action=action,
            success=verified,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get('HTTP_USER_AGENT', ''),
            details={'method': method}
        )
        
        if not verified:
            raise serializers.ValidationError("Invalid token or backup code")
        
        # Trust device if requested
        device_id = None
        if trust_device:
            import hashlib
            request = self.context['request']
            device_string = f"{request.META.get('REMOTE_ADDR')}_{request.META.get('HTTP_USER_AGENT', '')}"
            device_id = hashlib.sha256(device_string.encode()).hexdigest()
            
            TrustedDevice.create_trusted_device(
                user=user,
                device_id=device_id,
                device_name=f"Device from {request.META.get('REMOTE_ADDR')}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return {
            'verified': True,
            'method': method,
            'device_id': device_id
        }


class BackupCodesSerializer(serializers.Serializer):
    """Serializer for regenerating backup codes"""
    password = serializers.CharField(write_only=True)
    
    def validate_password(self, value):
        """Validate password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Invalid password")
        return value
    
    def create(self, validated_data):
        """Generate new backup codes"""
        user = self.context['request'].user
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=user, is_enabled=True)
            backup_codes = two_factor.generate_backup_codes()
            
            return {
                'success': True,
                'backup_codes': backup_codes,
                'message': 'New backup codes generated. Old codes are now invalid.'
            }
        except TwoFactorAuth.DoesNotExist:
            raise serializers.ValidationError("2FA not enabled")


class TrustedDeviceSerializer(serializers.ModelSerializer):
    """Serializer for trusted devices"""
    
    class Meta:
        model = TrustedDevice
        fields = [
            'id', 'device_id', 'device_name', 'ip_address',
            'trusted_at', 'last_used', 'expires_at', 'is_active'
        ]
        read_only_fields = fields


class SecurityQuestionSerializer(serializers.ModelSerializer):
    """Serializer for security questions"""
    answer = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = SecurityQuestion
        fields = ['id', 'question', 'answer', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'answer': {'write_only': True}
        }
    
    def create(self, validated_data):
        """Create security question with hashed answer"""
        user = self.context['request'].user
        question = validated_data['question']
        answer = validated_data['answer']
        
        security_q = SecurityQuestion.objects.create(
            user=user,
            question=question
        )
        security_q.set_answer(answer)
        security_q.save()
        
        return security_q


__all__ = [
    'TwoFactorSetupSerializer',
    'TwoFactorVerifySerializer',
    'TwoFactorDisableSerializer',
    'TwoFactorLoginSerializer',
    'BackupCodesSerializer',
    'TrustedDeviceSerializer',
    'SecurityQuestionSerializer'
]
