"""
Security and 2FA API Views
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .security_models import TwoFactorAuth, TrustedDevice, SecurityQuestion, TwoFactorAuthLog
from .security_serializers import (
    TwoFactorSetupSerializer, TwoFactorVerifySerializer,
    TwoFactorDisableSerializer, BackupCodesSerializer,
    TrustedDeviceSerializer, SecurityQuestionSerializer
)

User = get_user_model()


class TwoFactorAuthViewSet(viewsets.ViewSet):
    """
    ViewSet for Two-Factor Authentication management
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get 2FA status for current user
        
        GET /api/accounts/2fa/status/
        """
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
            return Response({
                'enabled': two_factor.is_enabled,
                'enabled_at': two_factor.enabled_at,
                'last_used': two_factor.last_used,
                'backup_codes_remaining': len(two_factor.backup_codes)
            })
        except TwoFactorAuth.DoesNotExist:
            return Response({
                'enabled': False,
                'enabled_at': None,
                'last_used': None,
                'backup_codes_remaining': 0
            })
    
    @action(detail=False, methods=['post'])
    def setup(self, request):
        """
        Initiate 2FA setup
        
        POST /api/accounts/2fa/setup/
        """
        serializer = TwoFactorSetupSerializer(
            data={},
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verify 2FA setup and enable it
        
        POST /api/accounts/2fa/verify/
        {
            "token": "123456",
            "trust_device": false
        }
        """
        serializer = TwoFactorVerifySerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def disable(self, request):
        """
        Disable 2FA
        
        POST /api/accounts/2fa/disable/
        {
            "password": "user_password",
            "token": "123456"
        }
        """
        serializer = TwoFactorDisableSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def regenerate_backup_codes(self, request):
        """
        Regenerate backup codes
        
        POST /api/accounts/2fa/regenerate_backup_codes/
        {
            "password": "user_password"
        }
        """
        serializer = BackupCodesSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def logs(self, request):
        """
        Get 2FA activity logs
        
        GET /api/accounts/2fa/logs/
        """
        logs = TwoFactorAuthLog.objects.filter(user=request.user)[:50]
        
        data = [
            {
                'action': log.action,
                'success': log.success,
                'timestamp': log.timestamp,
                'ip_address': log.ip_address,
                'details': log.details
            }
            for log in logs
        ]
        
        return Response(data)


class TrustedDevicesViewSet(viewsets.ViewSet):
    """
    ViewSet for managing trusted devices
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """
        List all trusted devices
        
        GET /api/accounts/trusted-devices/
        """
        devices = TrustedDevice.objects.filter(
            user=request.user,
            is_active=True
        )
        
        serializer = TrustedDeviceSerializer(devices, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        Get specific trusted device
        
        GET /api/accounts/trusted-devices/{id}/
        """
        device = get_object_or_404(
            TrustedDevice,
            pk=pk,
            user=request.user
        )
        
        serializer = TrustedDeviceSerializer(device)
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        """
        Revoke trust for a device
        
        DELETE /api/accounts/trusted-devices/{id}/
        """
        device = get_object_or_404(
            TrustedDevice,
            pk=pk,
            user=request.user
        )
        
        device.revoke()
        
        return Response({
            'success': True,
            'message': 'Device trust revoked'
        })
    
    @action(detail=False, methods=['post'])
    def revoke_all(self, request):
        """
        Revoke all trusted devices
        
        POST /api/accounts/trusted-devices/revoke_all/
        """
        TrustedDevice.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False)
        
        return Response({
            'success': True,
            'message': 'All devices revoked'
        })
    
    @action(detail=False, methods=['post'])
    def check_device(self, request):
        """
        Check if current device is trusted
        
        POST /api/accounts/trusted-devices/check_device/
        {
            "device_id": "sha256_hash"
        }
        """
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response(
                {'error': 'device_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = TrustedDevice.objects.get(
                user=request.user,
                device_id=device_id,
                is_active=True
            )
            
            if device.is_valid():
                return Response({
                    'trusted': True,
                    'device_name': device.device_name,
                    'expires_at': device.expires_at
                })
        except TrustedDevice.DoesNotExist:
            pass
        
        return Response({'trusted': False})


class SecurityQuestionsViewSet(viewsets.ViewSet):
    """
    ViewSet for security questions
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """
        List security questions (without answers)
        
        GET /api/accounts/security-questions/
        """
        questions = SecurityQuestion.objects.filter(user=request.user)
        serializer = SecurityQuestionSerializer(questions, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """
        Create security question
        
        POST /api/accounts/security-questions/
        {
            "question": "What is your favorite color?",
            "answer": "blue"
        }
        """
        serializer = SecurityQuestionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'success': True, 'message': 'Security question created'},
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """
        Delete security question
        
        DELETE /api/accounts/security-questions/{id}/
        """
        question = get_object_or_404(
            SecurityQuestion,
            pk=pk,
            user=request.user
        )
        
        question.delete()
        
        return Response({
            'success': True,
            'message': 'Security question deleted'
        })
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """
        Verify answer to security question
        
        POST /api/accounts/security-questions/{id}/verify/
        {
            "answer": "blue"
        }
        """
        question = get_object_or_404(
            SecurityQuestion,
            pk=pk,
            user=request.user
        )
        
        answer = request.data.get('answer')
        
        if not answer:
            return Response(
                {'error': 'answer required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if question.check_answer(answer):
            return Response({'verified': True})
        else:
            return Response(
                {'verified': False, 'error': 'Incorrect answer'},
                status=status.HTTP_400_BAD_REQUEST
            )


__all__ = [
    'TwoFactorAuthViewSet',
    'TrustedDevicesViewSet',
    'SecurityQuestionsViewSet'
]
