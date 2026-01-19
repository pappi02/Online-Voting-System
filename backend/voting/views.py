"""
Voting views for iVote Systems
Handles vote casting, verification, and results
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from .models import Vote, VoteAudit, VoteVerification
from .serializers import (
    CastVoteSerializer, VoteVerificationSerializer,
    VoteStatusSerializer, VoteReceiptSerializer,
    VoteAuditSerializer, AdminVoteDetailSerializer,
    ElectionResultsSerializer
)
from elections.models import Election, Position, Candidate, ElectionVoter
from accounts.permissions import IsVerifiedVoter, IsElectionOfficial, IsSystemAdmin


class VotingViewSet(viewsets.ViewSet):
    """
    ViewSet for vote casting and verification
    """
    
    def get_permissions(self):
        """
        Permissions based on action
        """
        if self.action in ['cast_vote']:
            return [permissions.IsAuthenticated(), IsVerifiedVoter()]
        elif self.action in ['verify_vote']:
            return [permissions.AllowAny()]
        elif self.action in ['my_vote_status', 'my_votes']:
            return [permissions.IsAuthenticated(), IsVerifiedVoter()]
        elif self.action in ['audit_logs', 'vote_details', 'decrypt_vote']:
            return [permissions.IsAuthenticated(), IsSystemAdmin()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=False, methods=['post'])
    def cast_vote(self, request):
        """
        Cast a vote in an election
        
        POST /api/voting/cast_vote/
        {
            "election_id": "uuid",
            "votes": [
                {
                    "position_id": "uuid",
                    "candidate_ids": ["uuid1", "uuid2"]
                }
            ]
        }
        """
        serializer = CastVoteSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                result = serializer.save()
                receipt_serializer = VoteReceiptSerializer(result)
                return Response(
                    receipt_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def verify_vote(self, request):
        """
        Verify a vote using verification code
        
        POST /api/voting/verify_vote/
        {
            "verification_code": "ABC-DEF-GHI-JKL"
        }
        """
        serializer = VoteVerificationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def my_vote_status(self, request):
        """
        Check if user has voted in an election
        
        POST /api/voting/my_vote_status/
        {
            "election_id": "uuid"
        }
        """
        serializer = VoteStatusSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        election_id = serializer.validated_data['election_id']
        
        try:
            election = Election.objects.get(id=election_id)
            voter_profile = request.user.voter_profile
            
            # Check ElectionVoter status
            election_voter = ElectionVoter.objects.filter(
                election=election,
                voter=voter_profile
            ).first()
            
            if not election_voter:
                return Response({
                    'has_voted': False,
                    'status': 'not_eligible',
                    'message': 'Not eligible to vote in this election'
                })
            
            return Response({
                'has_voted': election_voter.status == 'voted',
                'status': election_voter.status,
                'voted_at': election_voter.voted_at,
                'can_vote': election_voter.status in ['invited', 'eligible'] and
                           election.status == 'ongoing'
            })
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def my_votes(self, request):
        """
        Get list of elections user has voted in (no vote content)
        
        GET /api/voting/my_votes/
        """
        try:
            voter_profile = request.user.voter_profile
            
            # Get elections where user has voted
            voted_elections = ElectionVoter.objects.filter(
                voter=voter_profile,
                status='voted'
            ).select_related('election')
            
            results = []
            for election_voter in voted_elections:
                results.append({
                    'election_id': election_voter.election.id,
                    'election_title': election_voter.election.title,
                    'voted_at': election_voter.voted_at,
                    'election_status': election_voter.election.status
                })
            
            return Response(results)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsSystemAdmin])
    def audit_logs(self, request):
        """
        Get vote audit logs (admin only)
        
        GET /api/voting/audit_logs/?election_id=uuid&action=vote_cast
        """
        queryset = VoteAudit.objects.all()
        
        # Filter by election
        election_id = request.query_params.get('election_id')
        if election_id:
            queryset = queryset.filter(election_id=election_id)
        
        # Filter by action
        action = request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Paginate
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size
        
        serializer = VoteAuditSerializer(
            queryset[start:end],
            many=True
        )
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsSystemAdmin])
    def vote_details(self, request, pk=None):
        """
        Get detailed vote information (admin only - includes decryption)
        
        GET /api/voting/{vote_id}/vote_details/
        """
        vote = get_object_or_404(Vote, pk=pk)
        serializer = AdminVoteDetailSerializer(vote, context={'request': request})
        return Response(serializer.data)


class ElectionResultsViewSet(viewsets.ViewSet):
    """
    ViewSet for election results
    """
    
    def get_permissions(self):
        """
        Results visible based on election status
        """
        if self.action in ['results', 'summary']:
            return [permissions.AllowAny()]
        elif self.action in ['generate_results']:
            return [permissions.IsAuthenticated(), IsElectionOfficial()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Get election results
        
        GET /api/voting/elections/{election_id}/results/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Check if results should be visible
        if election.status not in ['completed', 'results_published']:
            if not request.user.is_staff:
                return Response(
                    {'error': 'Results not yet available'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Calculate results
        results = self._calculate_results(election)
        
        serializer = ElectionResultsSerializer(results)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get election voting summary
        
        GET /api/voting/elections/{election_id}/summary/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Count votes
        total_votes = Vote.objects.filter(election=election).count()
        verified_votes = Vote.objects.filter(
            election=election,
            verified_at__isnull=False
        ).count()
        
        # Count eligible voters
        eligible_voters = ElectionVoter.objects.filter(
            election=election,
            status__in=['invited', 'eligible', 'voted']
        ).count()
        
        # Turnout percentage
        turnout = 0
        if eligible_voters > 0:
            turnout = (total_votes / eligible_voters) * 100
        
        return Response({
            'election_id': election.id,
            'election_title': election.title,
            'status': election.status,
            'total_votes': total_votes,
            'verified_votes': verified_votes,
            'eligible_voters': eligible_voters,
            'turnout_percentage': round(turnout, 2),
            'voting_open': election.status == 'ongoing'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsElectionOfficial])
    def generate_results(self, request, pk=None):
        """
        Generate and finalize election results (admin only)
        
        POST /api/voting/elections/{election_id}/generate_results/
        """
        election = get_object_or_404(Election, pk=pk)
        
        # Check if election is completed
        if election.status != 'completed':
            return Response(
                {'error': 'Election must be completed before generating results'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate results
        results = self._calculate_results(election)
        
        # Update election status
        election.status = 'results_published'
        election.save(update_fields=['status'])
        
        # Audit log
        VoteAudit.log_action(
            action='results_generated',
            election=election,
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            details={
                'total_votes': results['total_votes'],
                'positions_count': len(results['positions'])
            }
        )
        
        return Response({
            'message': 'Results generated successfully',
            'results': results
        })
    
    def _calculate_results(self, election):
        """
        Calculate election results by decrypting and tallying votes
        """
        # Get all votes for this election
        votes = Vote.objects.filter(election=election)
        
        # Initialize results structure
        results = {
            'election_id': str(election.id),
            'election_title': election.title,
            'total_votes': votes.count(),
            'positions': [],
            'generated_at': timezone.now()
        }
        
        # Get all positions
        positions = election.positions.all().prefetch_related('candidates')
        
        for position in positions:
            position_result = {
                'position_id': str(position.id),
                'position_title': position.title,
                'candidates_to_elect': position.candidates_per_voter,
                'candidates': []
            }
            
            # Count votes for each candidate
            candidate_votes = {}
            
            for vote in votes:
                try:
                    # Decrypt vote
                    vote_data = vote.decrypt_vote_data()
                    
                    # Get votes for this position
                    position_votes = vote_data.get(str(position.id), [])
                    
                    # Count each candidate
                    for candidate_id in position_votes:
                        candidate_votes[candidate_id] = candidate_votes.get(candidate_id, 0) + 1
                
                except Exception as e:
                    # Log error but continue
                    VoteAudit.log_action(
                        action='vote_decrypted',
                        election=election,
                        vote=vote,
                        details={'error': str(e), 'context': 'results_calculation'}
                    )
            
            # Add candidate details and vote counts
            for candidate in position.candidates.filter(status='approved'):
                candidate_id = str(candidate.id)
                vote_count = candidate_votes.get(candidate_id, 0)
                
                position_result['candidates'].append({
                    'candidate_id': candidate_id,
                    'name': candidate.name,
                    'party': candidate.party,
                    'photo_url': candidate.photo.url if candidate.photo else None,
                    'votes': vote_count,
                    'percentage': round(
                        (vote_count / results['total_votes'] * 100) if results['total_votes'] > 0 else 0,
                        2
                    )
                })
            
            # Sort candidates by vote count (descending)
            position_result['candidates'].sort(key=lambda x: x['votes'], reverse=True)
            
            results['positions'].append(position_result)
        
        return results


__all__ = [
    'VotingViewSet',
    'ElectionResultsViewSet',
]
