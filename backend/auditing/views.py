"""
Audit and Security API Views
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .audit_models import AuditLog, SecurityEvent, LoginAttempt
from .security_monitor import SecurityMonitor
from .session_management import SessionManager

User = get_user_model()


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get audit logs based on user permissions"""
        user = self.request.user
        
        if user.is_staff:
            # Staff can see all logs
            return AuditLog.objects.all()
        else:
            # Regular users can only see their own logs
            return AuditLog.objects.filter(user=user)
    
    def list(self, request):
        """
        List audit logs with filtering
        
        GET /api/auditing/logs/?action=login&days=7
        """
        queryset = self.get_queryset()
        
        # Filter by action
        action = request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by severity
        severity = request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by date range
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
            start_date = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(timestamp__gte=start_date)
        except (ValueError, TypeError):
            pass
        
        # Limit results
        queryset = queryset[:100]
        
        data = [
            {
                'id': log.id,
                'user': log.user.email if log.user else None,
                'action': log.action,
                'severity': log.severity,
                'ip_address': log.ip_address,
                'request_path': log.request_path,
                'success': log.success,
                'timestamp': log.timestamp,
                'details': log.details
            }
            for log in queryset
        ]
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get audit log summary
        
        GET /api/auditing/logs/summary/
        """
        queryset = self.get_queryset()
        
        # Get counts by action
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        recent_logs = queryset.filter(timestamp__gte=start_date)
        
        # Action counts
        action_counts = {}
        for action, _ in AuditLog.ACTION_CHOICES:
            count = recent_logs.filter(action=action).count()
            if count > 0:
                action_counts[action] = count
        
        # Severity counts
        severity_counts = {
            'info': recent_logs.filter(severity=AuditLog.SEVERITY_INFO).count(),
            'warning': recent_logs.filter(severity=AuditLog.SEVERITY_WARNING).count(),
            'error': recent_logs.filter(severity=AuditLog.SEVERITY_ERROR).count(),
            'critical': recent_logs.filter(severity=AuditLog.SEVERITY_CRITICAL).count(),
        }
        
        return Response({
            'period_days': days,
            'total_events': recent_logs.count(),
            'action_counts': action_counts,
            'severity_counts': severity_counts
        })


class SecurityEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing security events
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Get security events"""
        queryset = SecurityEvent.objects.all()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        return queryset[:100]
    
    def list(self, request):
        """
        List security events
        
        GET /api/auditing/security-events/?status=open
        """
        queryset = self.get_queryset()
        
        data = [
            {
                'id': event.id,
                'event_type': event.event_type,
                'status': event.status,
                'user': event.user.email if event.user else None,
                'ip_address': event.ip_address,
                'description': event.description,
                'risk_score': event.risk_score,
                'auto_blocked': event.auto_blocked,
                'created_at': event.created_at,
                'resolved_at': event.resolved_at
            }
            for event in queryset
        ]
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Resolve security event
        
        POST /api/auditing/security-events/{id}/resolve/
        {
            "notes": "False positive - legitimate user"
        }
        """
        event = self.get_object()
        notes = request.data.get('notes', '')
        
        event.resolve(resolved_by=request.user, notes=notes)
        
        return Response({
            'success': True,
            'message': 'Security event resolved'
        })
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get security dashboard data
        
        GET /api/auditing/security-events/dashboard/
        """
        # Recent events
        recent_events = SecurityEvent.objects.all()[:20]
        
        # Open events by type
        open_events = SecurityEvent.objects.filter(status=SecurityEvent.STATUS_OPEN)
        
        event_type_counts = {}
        for event_type, _ in SecurityEvent.EVENT_CHOICES:
            count = open_events.filter(event_type=event_type).count()
            if count > 0:
                event_type_counts[event_type] = count
        
        # High risk events
        high_risk = SecurityEvent.objects.filter(
            risk_score__gte=70,
            status=SecurityEvent.STATUS_OPEN
        ).count()
        
        return Response({
            'open_events': open_events.count(),
            'high_risk_events': high_risk,
            'event_type_counts': event_type_counts,
            'recent_events': [
                {
                    'id': event.id,
                    'event_type': event.event_type,
                    'risk_score': event.risk_score,
                    'created_at': event.created_at
                }
                for event in recent_events
            ]
        })


class SecurityMonitorViewSet(viewsets.ViewSet):
    """
    ViewSet for security monitoring
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def risk_profile(self, request):
        """
        Get risk profile for current user
        
        GET /api/auditing/monitor/risk_profile/
        """
        profile = SecurityMonitor.get_user_risk_profile(request.user)
        return Response(profile)
    
    @action(detail=False, methods=['post'])
    def analyze_login(self, request):
        """
        Analyze login risk
        
        POST /api/auditing/monitor/analyze_login/
        {
            "username": "user@example.com"
        }
        
        (Admin only)
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        username = request.data.get('username')
        
        if not username:
            return Response(
                {'error': 'username required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        ip_address = SecurityMonitor._get_client_ip(request)
        analysis = SecurityMonitor.analyze_login_risk(user, ip_address)
        
        return Response(analysis)
    
    @action(detail=False, methods=['get'])
    def login_attempts(self, request):
        """
        Get recent login attempts
        
        GET /api/auditing/monitor/login_attempts/?days=7
        """
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        if request.user.is_staff:
            # Staff can see all attempts
            attempts = LoginAttempt.objects.filter(timestamp__gte=start_date)[:100]
        else:
            # Users can see their own attempts
            attempts = LoginAttempt.objects.filter(
                user=request.user,
                timestamp__gte=start_date
            )[:50]
        
        data = [
            {
                'username': attempt.username,
                'success': attempt.success,
                'failure_reason': attempt.failure_reason,
                'ip_address': attempt.ip_address,
                'two_factor_required': attempt.two_factor_required,
                'two_factor_success': attempt.two_factor_success,
                'timestamp': attempt.timestamp
            }
            for attempt in attempts
        ]
        
        return Response(data)


class SessionManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for session management
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def active_sessions(self, request):
        """
        Get active sessions for current user
        
        GET /api/auditing/sessions/active_sessions/
        """
        sessions = SessionManager.get_user_sessions(request.user)
        
        session_data = []
        for session_key in sessions:
            info = SessionManager.get_session_info(session_key)
            if info:
                # Mark current session
                info['is_current'] = session_key == request.session.session_key
                session_data.append(info)
        
        return Response(session_data)
    
    @action(detail=False, methods=['post'])
    def invalidate_session(self, request):
        """
        Invalidate specific session
        
        POST /api/auditing/sessions/invalidate_session/
        {
            "session_key": "abc123..."
        }
        """
        session_key = request.data.get('session_key')
        
        if not session_key:
            return Response(
                {'error': 'session_key required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify session belongs to user
        sessions = SessionManager.get_user_sessions(request.user)
        
        if session_key not in sessions:
            return Response(
                {'error': 'Session not found or unauthorized'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        SessionManager.invalidate_session(session_key)
        
        return Response({
            'success': True,
            'message': 'Session invalidated'
        })
    
    @action(detail=False, methods=['post'])
    def invalidate_all(self, request):
        """
        Invalidate all sessions except current
        
        POST /api/auditing/sessions/invalidate_all/
        """
        current_session = request.session.session_key
        
        SessionManager.invalidate_user_sessions(
            user=request.user,
            exclude_session=current_session
        )
        
        return Response({
            'success': True,
            'message': 'All other sessions invalidated'
        })


__all__ = [
    'AuditLogViewSet',
    'SecurityEventViewSet',
    'SecurityMonitorViewSet',
    'SessionManagementViewSet'
]
