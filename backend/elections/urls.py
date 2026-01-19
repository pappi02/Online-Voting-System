"""
Elections app URL routing
Configures all election endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
	ElectionViewSet, PositionViewSet, CandidateViewSet,
	ElectionVoterViewSet, ElectionScheduleViewSet, ElectionInviteViewSet
)

app_name = 'elections'

# Main router for elections
router = DefaultRouter()
router.register(r'elections', ElectionViewSet, basename='election')

# Nested routers for nested endpoints
elections_router = routers.NestedDefaultRouter(router, 'elections', lookup='election')
elections_router.register(r'positions', PositionViewSet, basename='position')
elections_router.register(r'voters', ElectionVoterViewSet, basename='election-voter')
elections_router.register(r'schedule', ElectionScheduleViewSet, basename='schedule')

# Nested positions router
positions_router = routers.NestedDefaultRouter(elections_router, 'positions', lookup='position')
positions_router.register(r'candidates', CandidateViewSet, basename='candidate')
positions_router.register(r'invites', ElectionInviteViewSet, basename='invite')

urlpatterns = [
	path('', include(router.urls)),
	path('', include(elections_router.urls)),
	path('', include(positions_router.urls)),
]

urlpatterns = []
