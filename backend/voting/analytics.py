"""
Analytics and statistics utilities for voting system
Provides vote counting, turnout analysis, and statistical calculations
"""

from django.db.models import Count, Q, F, Sum, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
import json

from .models import Vote, VoteAudit
from elections.models import Election, Position, Candidate, ElectionVoter


class VoteAnalytics:
    """
    Comprehensive analytics for election results and statistics
    """
    
    def __init__(self, election):
        self.election = election
        self._cache = {}
    
    def get_total_votes(self):
        """Get total number of votes cast"""
        if 'total_votes' not in self._cache:
            self._cache['total_votes'] = Vote.objects.filter(
                election=self.election
            ).count()
        return self._cache['total_votes']
    
    def get_verified_votes(self):
        """Get number of verified votes"""
        if 'verified_votes' not in self._cache:
            self._cache['verified_votes'] = Vote.objects.filter(
                election=self.election,
                verified_at__isnull=False
            ).count()
        return self._cache['verified_votes']
    
    def get_eligible_voters(self):
        """Get number of eligible voters"""
        if 'eligible_voters' not in self._cache:
            self._cache['eligible_voters'] = ElectionVoter.objects.filter(
                election=self.election,
                status__in=['invited', 'eligible', 'voted']
            ).count()
        return self._cache['eligible_voters']
    
    def get_turnout_percentage(self):
        """Calculate voter turnout percentage"""
        total_votes = self.get_total_votes()
        eligible_voters = self.get_eligible_voters()
        
        if eligible_voters == 0:
            return 0.0
        
        return round((total_votes / eligible_voters) * 100, 2)
    
    def get_verification_rate(self):
        """Calculate percentage of verified votes"""
        total_votes = self.get_total_votes()
        verified_votes = self.get_verified_votes()
        
        if total_votes == 0:
            return 0.0
        
        return round((verified_votes / total_votes) * 100, 2)
    
    def get_votes_by_hour(self):
        """Get vote distribution by hour"""
        votes = Vote.objects.filter(election=self.election).values(
            'cast_at__hour'
        ).annotate(count=Count('id')).order_by('cast_at__hour')
        
        # Create 24-hour distribution
        distribution = {hour: 0 for hour in range(24)}
        for vote in votes:
            hour = vote['cast_at__hour']
            distribution[hour] = vote['count']
        
        return [
            {'hour': hour, 'votes': count}
            for hour, count in distribution.items()
        ]
    
    def get_votes_by_day(self):
        """Get vote distribution by day"""
        votes = Vote.objects.filter(election=self.election).values(
            'cast_at__date'
        ).annotate(count=Count('id')).order_by('cast_at__date')
        
        return [
            {
                'date': str(vote['cast_at__date']),
                'votes': vote['count']
            }
            for vote in votes
        ]
    
    def get_position_statistics(self):
        """Get statistics for each position"""
        positions = self.election.positions.all().prefetch_related('candidates')
        results = []
        
        for position in positions:
            # Get all votes
            all_votes = Vote.objects.filter(election=self.election)
            total_votes = all_votes.count()
            
            # Count votes for this position
            position_vote_count = 0
            candidate_votes = defaultdict(int)
            
            for vote in all_votes:
                try:
                    vote_data = vote.decrypt_vote_data()
                    position_votes = vote_data.get(str(position.id), [])
                    
                    if position_votes:
                        position_vote_count += 1
                        for candidate_id in position_votes:
                            candidate_votes[candidate_id] += 1
                except Exception:
                    continue
            
            # Calculate participation rate for this position
            participation_rate = 0
            if total_votes > 0:
                participation_rate = round((position_vote_count / total_votes) * 100, 2)
            
            # Get candidate statistics
            candidates_data = []
            for candidate in position.candidates.filter(status='approved'):
                votes_count = candidate_votes.get(str(candidate.id), 0)
                vote_percentage = 0
                if position_vote_count > 0:
                    vote_percentage = round((votes_count / position_vote_count) * 100, 2)
                
                candidates_data.append({
                    'id': str(candidate.id),
                    'name': candidate.name,
                    'party': candidate.party,
                    'votes': votes_count,
                    'percentage': vote_percentage
                })
            
            # Sort by votes (descending)
            candidates_data.sort(key=lambda x: x['votes'], reverse=True)
            
            results.append({
                'position_id': str(position.id),
                'position_title': position.title,
                'total_votes': position_vote_count,
                'participation_rate': participation_rate,
                'candidates_per_voter': position.candidates_per_voter,
                'candidates': candidates_data,
                'winner': candidates_data[0] if candidates_data else None
            })
        
        return results
    
    def get_summary_statistics(self):
        """Get comprehensive election summary"""
        return {
            'election_id': str(self.election.id),
            'election_title': self.election.title,
            'election_type': self.election.election_type,
            'status': self.election.status,
            'scheduled_start': self.election.scheduled_start,
            'scheduled_end': self.election.scheduled_end,
            'total_votes': self.get_total_votes(),
            'verified_votes': self.get_verified_votes(),
            'eligible_voters': self.get_eligible_voters(),
            'turnout_percentage': self.get_turnout_percentage(),
            'verification_rate': self.get_verification_rate(),
            'positions_count': self.election.positions.count(),
            'candidates_count': Candidate.objects.filter(
                position__election=self.election,
                status='approved'
            ).count(),
        }
    
    def get_audit_statistics(self):
        """Get audit trail statistics"""
        audits = VoteAudit.objects.filter(election=self.election)
        
        action_counts = audits.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_audits': audits.count(),
            'actions': [
                {
                    'action': audit['action'],
                    'count': audit['count']
                }
                for audit in action_counts
            ],
            'first_action': audits.order_by('timestamp').first(),
            'last_action': audits.order_by('-timestamp').first()
        }
    
    def get_complete_report(self):
        """Generate complete analytics report"""
        return {
            'summary': self.get_summary_statistics(),
            'positions': self.get_position_statistics(),
            'turnout': {
                'by_hour': self.get_votes_by_hour(),
                'by_day': self.get_votes_by_day()
            },
            'audit': self.get_audit_statistics(),
            'generated_at': timezone.now()
        }


class TurnoutAnalytics:
    """
    Analyze voter turnout patterns and demographics
    """
    
    @staticmethod
    def get_turnout_trend(election):
        """Get hourly turnout trend"""
        votes = Vote.objects.filter(election=election).order_by('cast_at')
        
        if not votes.exists():
            return []
        
        start_time = votes.first().cast_at
        trend = []
        cumulative_votes = 0
        
        for vote in votes:
            cumulative_votes += 1
            hours_elapsed = (vote.cast_at - start_time).total_seconds() / 3600
            
            trend.append({
                'timestamp': vote.cast_at,
                'cumulative_votes': cumulative_votes,
                'hours_elapsed': round(hours_elapsed, 2)
            })
        
        return trend
    
    @staticmethod
    def get_peak_voting_times(election):
        """Identify peak voting periods"""
        votes_by_hour = Vote.objects.filter(election=election).values(
            'cast_at__hour'
        ).annotate(count=Count('id')).order_by('-count')
        
        return [
            {
                'hour': vote['cast_at__hour'],
                'votes': vote['count'],
                'period': TurnoutAnalytics._get_period_name(vote['cast_at__hour'])
            }
            for vote in votes_by_hour[:5]  # Top 5 hours
        ]
    
    @staticmethod
    def _get_period_name(hour):
        """Get friendly period name for hour"""
        if 6 <= hour < 12:
            return 'Morning (6AM-12PM)'
        elif 12 <= hour < 18:
            return 'Afternoon (12PM-6PM)'
        elif 18 <= hour < 24:
            return 'Evening (6PM-12AM)'
        else:
            return 'Night (12AM-6AM)'
    
    @staticmethod
    def get_participation_gaps(election):
        """Identify voters who haven't voted yet"""
        eligible = ElectionVoter.objects.filter(
            election=election,
            status__in=['invited', 'eligible']
        ).count()
        
        voted = ElectionVoter.objects.filter(
            election=election,
            status='voted'
        ).count()
        
        return {
            'eligible_not_voted': eligible,
            'voted': voted,
            'participation_rate': round((voted / (eligible + voted) * 100), 2) if (eligible + voted) > 0 else 0
        }


class ComparisonAnalytics:
    """
    Compare elections and historical data
    """
    
    @staticmethod
    def compare_elections(election_ids):
        """Compare multiple elections"""
        elections = Election.objects.filter(id__in=election_ids)
        comparisons = []
        
        for election in elections:
            analytics = VoteAnalytics(election)
            comparisons.append({
                'election_id': str(election.id),
                'title': election.title,
                'total_votes': analytics.get_total_votes(),
                'eligible_voters': analytics.get_eligible_voters(),
                'turnout_percentage': analytics.get_turnout_percentage(),
                'positions_count': election.positions.count(),
                'scheduled_start': election.scheduled_start,
                'scheduled_end': election.scheduled_end
            })
        
        return comparisons
    
    @staticmethod
    def get_historical_trends(election_type=None, limit=10):
        """Get historical election trends"""
        queryset = Election.objects.filter(
            status__in=['completed', 'results_published']
        ).order_by('-scheduled_start')
        
        if election_type:
            queryset = queryset.filter(election_type=election_type)
        
        elections = queryset[:limit]
        trends = []
        
        for election in elections:
            analytics = VoteAnalytics(election)
            trends.append({
                'election_id': str(election.id),
                'title': election.title,
                'date': election.scheduled_start,
                'turnout': analytics.get_turnout_percentage(),
                'total_votes': analytics.get_total_votes()
            })
        
        return trends


__all__ = [
    'VoteAnalytics',
    'TurnoutAnalytics',
    'ComparisonAnalytics'
]
