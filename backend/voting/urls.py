"""
URL configuration for voting app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VotingViewSet, ElectionResultsViewSet
from .analytics_views import AnalyticsViewSet, ExportViewSet
from .realtime_views import RealTimeViewSet

app_name = 'voting'

# Create router
router = DefaultRouter()
router.register(r'votes', VotingViewSet, basename='vote')
router.register(r'results', ElectionResultsViewSet, basename='results')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'exports', ExportViewSet, basename='exports')
router.register(r'realtime', RealTimeViewSet, basename='realtime')

urlpatterns = [
    path('', include(router.urls)),
]
