"""
URL configuration for auditing app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuditLogViewSet,
    SecurityEventViewSet,
    SecurityMonitorViewSet,
    SessionManagementViewSet
)

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-logs')
router.register(r'security-events', SecurityEventViewSet, basename='security-events')
router.register(r'monitor', SecurityMonitorViewSet, basename='security-monitor')
router.register(r'sessions', SessionManagementViewSet, basename='session-management')

app_name = 'auditing'

urlpatterns = [
    path('', include(router.urls)),
]
