"""
Election app API views
Complete election management endpoints with permissions
"""

from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
	Election, Position, Candidate, ElectionVoter,
	ElectionSchedule, ElectionInvite
)
from .serializers import (
	ElectionListSerializer, ElectionDetailSerializer, ElectionCreateSerializer,
	PositionListSerializer, PositionDetailSerializer, PositionCreateSerializer,
	CandidateListSerializer, CandidateDetailSerializer, CandidateCreateSerializer,
	CandidateApprovalSerializer, ElectionVoterSerializer, ElectionScheduleSerializer,
	ElectionInviteSerializer, ElectionInviteCreateSerializer
)
# Permissions from accounts app are handled via custom checks in this module


class IsElectionCreatorOrAdmin(permissions.BasePermission):
	"""Permission to edit only own elections or admin elections"""
    
	def has_object_permission(self, request, view, obj):
		if request.user.is_staff:
			return True
		return obj.created_by == request.user


class ElectionViewSet(viewsets.ModelViewSet):
	"""
	Complete election management viewset
    
	Endpoints:
	- GET /elections/ - List all elections
	- POST /elections/ - Create new election
	- GET /elections/{id}/ - Get election details
	- PUT /elections/{id}/ - Update election
	- DELETE /elections/{id}/ - Delete election
	- POST /elections/{id}/schedule_start/ - Schedule election start
	- POST /elections/{id}/close/ - Close election voting
	- GET /elections/{id}/candidates/ - Get all candidates
	- GET /elections/{id}/voters/ - Get voter participation
	- GET /elections/{id}/results/ - Get preliminary results
	"""
    
	queryset = Election.objects.all()
	filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
	filterset_fields = ['status', 'election_type']
	search_fields = ['title', 'description']
	ordering_fields = ['scheduled_start', 'created_at', 'title']
	ordering = ['-scheduled_start']
    
	def get_serializer_class(self):
		if self.action == 'list':
			return ElectionListSerializer
		elif self.action == 'create':
			return ElectionCreateSerializer
		return ElectionDetailSerializer
    
	def get_permissions(self):
		if self.action in ['create']:
			permission_classes = [permissions.IsAuthenticated]
		elif self.action in ['update', 'partial_update', 'destroy']:
			permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		else:
			permission_classes = [permissions.IsAuthenticated]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		user = self.request.user
		if user.is_staff:
			return Election.objects.all()
		return Election.objects.filter(
			Q(created_by=user) |
			Q(status__in=['active', 'scheduled', 'closed'])
		).distinct()
    
	@action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsElectionCreatorOrAdmin])
	def schedule_start(self, request, pk=None):
		"""Schedule when the election will start"""
		election = self.get_object()
        
		if election.status != 'scheduled':
			return Response(
				{'error': 'Can only schedule start for scheduled elections'},
				status=status.HTTP_400_BAD_REQUEST
			)
        
		election.status = 'active'
		election.save(update_fields=['status'])
        
		return Response(
			{'status': 'Election started'},
			status=status.HTTP_200_OK
		)
    
	@action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsElectionCreatorOrAdmin])
	def close(self, request, pk=None):
		"""Close election voting"""
		election = self.get_object()
        
		if election.status != 'active':
			return Response(
				{'error': 'Can only close active elections'},
				status=status.HTTP_400_BAD_REQUEST
			)
        
		election.status = 'closed'
		election.save(update_fields=['status'])
        
		return Response(
			{'status': 'Election closed'},
			status=status.HTTP_200_OK
		)
    
	@action(detail=True, methods=['get'])
	def candidates(self, request, pk=None):
		"""Get all approved candidates in election"""
		election = self.get_object()
		candidates = Candidate.objects.filter(
			position__election=election,
			status='approved'
		)
		serializer = CandidateListSerializer(candidates, many=True)
		return Response(serializer.data)
    
	@action(detail=True, methods=['get'])
	def voters(self, request, pk=None):
		"""Get voter participation stats"""
		election = self.get_object()
        
		# Only admins and election creator can see voter details
		if not (request.user.is_staff or election.created_by == request.user):
			return Response(
				{'error': 'Permission denied'},
				status=status.HTTP_403_FORBIDDEN
			)
        
		stats = {
			'total_eligible': election.get_voter_count(),
			'total_voted': ElectionVoter.objects.filter(
				election=election,
				status='voted'
			).count(),
			'total_abstained': ElectionVoter.objects.filter(
				election=election,
				status='abstained'
			).count(),
			'participation_rate': election.get_participation_rate()
		}
		return Response(stats)
    
	@action(detail=True, methods=['get'])
	def results(self, request, pk=None):
		"""Get preliminary election results"""
		election = self.get_object()
        
		if not election.results_visible_before_close and election.status != 'closed':
			return Response(
				{'error': 'Results not yet available'},
				status=status.HTTP_403_FORBIDDEN
			)
        
		results = []
		for position in election.positions.all():
			candidates = position.get_candidates().annotate(
				vote_count=Count('votes')
			).order_by('-vote_count')
            
			results.append({
				'position': position.title,
				'candidates': [
					{
						'id': c.id,
						'name': c.full_name,
						'votes': c.vote_count
					}
					for c in candidates
				]
			})
        
		return Response(results)


class PositionViewSet(viewsets.ModelViewSet):
	"""
	Position management viewset
    
	Endpoints:
	- GET /elections/{election_id}/positions/ - List positions
	- POST /elections/{election_id}/positions/ - Create position
	- GET /elections/{election_id}/positions/{id}/ - Get position details
	- PUT /elections/{election_id}/positions/{id}/ - Update position
	"""
    
	queryset = Position.objects.all()
	filter_backends = [filters.OrderingFilter]
	ordering = ['display_order']
    
	def get_serializer_class(self):
		if self.action == 'create':
			return PositionCreateSerializer
		elif self.action == 'list':
			return PositionListSerializer
		return PositionDetailSerializer
    
	def get_permissions(self):
		if self.action in ['create', 'update', 'partial_update', 'destroy']:
			permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		else:
			permission_classes = [permissions.IsAuthenticated]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		election_id = self.kwargs.get('election_id')
		return Position.objects.filter(election_id=election_id)
    
	def perform_create(self, serializer):
		election_id = self.kwargs.get('election_id')
		election = get_object_or_404(Election, id=election_id)
        
		# Check permission
		if not (self.request.user.is_staff or election.created_by == self.request.user):
			self.permission_denied(self.request)
        
		serializer.save(election=election)


class CandidateViewSet(viewsets.ModelViewSet):
	"""
	Candidate management viewset
    
	Endpoints:
	- GET /elections/{election_id}/positions/{position_id}/candidates/ - List candidates
	- POST /elections/{election_id}/positions/{position_id}/candidates/ - Register as candidate
	- GET /elections/{election_id}/positions/{position_id}/candidates/{id}/ - Get candidate details
	- POST /elections/{election_id}/positions/{position_id}/candidates/{id}/approve/ - Approve candidate
	- POST /elections/{election_id}/positions/{position_id}/candidates/{id}/reject/ - Reject candidate
	- POST /elections/{election_id}/positions/{position_id}/candidates/{id}/withdraw/ - Withdraw candidacy
	"""
    
	queryset = Candidate.objects.all()
    
	def get_serializer_class(self):
		if self.action == 'create':
			return CandidateCreateSerializer
		elif self.action in ['approve', 'reject']:
			return CandidateApprovalSerializer
		elif self.action == 'list':
			return CandidateListSerializer
		return CandidateDetailSerializer
    
	def get_permissions(self):
		if self.action == 'create':
			permission_classes = [permissions.IsAuthenticated]
		elif self.action in ['approve', 'reject']:
			permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		else:
			permission_classes = [permissions.IsAuthenticated]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		position_id = self.kwargs.get('position_id')
		return Candidate.objects.filter(position_id=position_id)
    
	def perform_create(self, serializer):
		position_id = self.kwargs.get('position_id')
		position = get_object_or_404(Position, id=position_id)
		serializer.save(position=position)
    
	@action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsElectionCreatorOrAdmin])
	def approve(self, request, pk=None, **kwargs):
		"""Approve candidate"""
		candidate = self.get_object()
		serializer = CandidateApprovalSerializer(candidate, data={'status': 'approved', **request.data}, partial=True)
        
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
	@action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsElectionCreatorOrAdmin])
	def reject(self, request, pk=None, **kwargs):
		"""Reject candidate"""
		candidate = self.get_object()
		serializer = CandidateApprovalSerializer(candidate, data={'status': 'rejected', **request.data}, partial=True)
        
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
	@action(detail=True, methods=['post'])
	def withdraw(self, request, pk=None, **kwargs):
		"""Withdraw from candidacy"""
		candidate = self.get_object()
        
		# Can only withdraw if you're the candidate or an admin
		if candidate.user != request.user and not request.user.is_staff:
			return Response(
				{'error': 'Permission denied'},
				status=status.HTTP_403_FORBIDDEN
			)
        
		candidate.withdraw()
		return Response({'status': 'Withdrawn from candidacy'})


class ElectionVoterViewSet(viewsets.ReadOnlyModelViewSet):
	"""
	Election voter tracking (read-only)
    
	Endpoints:
	- GET /elections/{election_id}/voters/ - List voter participation
	"""
    
	serializer_class = ElectionVoterSerializer
	filter_backends = [DjangoFilterBackend]
	filterset_fields = ['status']
    
	def get_permissions(self):
		permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		election_id = self.kwargs.get('election_id')
		election = get_object_or_404(Election, id=election_id)
        
		# Check permission
		if not (self.request.user.is_staff or election.created_by == self.request.user):
			self.permission_denied(self.request)
        
		return ElectionVoter.objects.filter(election_id=election_id)


class ElectionScheduleViewSet(viewsets.ModelViewSet):
	"""
	Election scheduling (state management)
    
	Endpoints:
	- GET /elections/{election_id}/schedule/ - Get election schedule
	- POST /elections/{election_id}/schedule/ - Update schedule
	"""
    
	serializer_class = ElectionScheduleSerializer
    
	def get_permissions(self):
		permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		election_id = self.kwargs.get('election_id')
		return ElectionSchedule.objects.filter(election_id=election_id)


class ElectionInviteViewSet(viewsets.ModelViewSet):
	"""
	Candidate invitation management
    
	Endpoints:
	- GET /elections/{election_id}/positions/{position_id}/invites/ - List invites
	- POST /elections/{election_id}/positions/{position_id}/invites/ - Send invite
	- POST /elections/{election_id}/positions/{position_id}/invites/{id}/accept/ - Accept invite
	"""
    
	queryset = ElectionInvite.objects.all()
	filter_backends = [DjangoFilterBackend]
	filterset_fields = ['status']
    
	def get_serializer_class(self):
		if self.action == 'create':
			return ElectionInviteCreateSerializer
		return ElectionInviteSerializer
    
	def get_permissions(self):
		if self.action == 'create':
			permission_classes = [permissions.IsAuthenticated, IsElectionCreatorOrAdmin]
		elif self.action == 'accept':
			permission_classes = [permissions.IsAuthenticated]
		else:
			permission_classes = [permissions.IsAuthenticated]
		return [permission() for permission in permission_classes]
    
	def get_queryset(self):
		position_id = self.kwargs.get('position_id')
		return ElectionInvite.objects.filter(position_id=position_id)
    
	def perform_create(self, serializer):
		election_id = self.kwargs.get('election_id')
		position_id = self.kwargs.get('position_id')
		election = get_object_or_404(Election, id=election_id)
        
		# Check permission
		if not (self.request.user.is_staff or election.created_by == self.request.user):
			self.permission_denied(self.request)
        
		serializer.save()
    
	@action(detail=True, methods=['post'])
	def accept(self, request, pk=None, **kwargs):
		"""Accept candidate invitation"""
		invite = self.get_object()
        
		if invite.is_expired():
			return Response(
				{'error': 'Invitation has expired'},
				status=status.HTTP_400_BAD_REQUEST
			)
        
		if invite.status != 'sent':
			return Response(
				{'error': 'Invitation already processed'},
				status=status.HTTP_400_BAD_REQUEST
			)
        
		invite.accept(request.user)
        
		# Create candidate record
		Candidate.objects.create(
			position=invite.position,
			user=request.user,
			full_name=request.user.get_full_name() or request.user.username,
			status='approved'
		)
        
		return Response({'status': 'Invitation accepted'})


__all__ = [
	'ElectionViewSet',
	'PositionViewSet',
	'CandidateViewSet',
	'ElectionVoterViewSet',
	'ElectionScheduleViewSet',
	'ElectionInviteViewSet',
]
