"""
Phase 5: Results & Analytics Tests
Tests for analytics, reporting, and export functionality
"""

import pytest
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import json

from elections.models import Election, Position, Candidate, ElectionVoter
from accounts.models import VoterProfile
from voting.models import Vote, VoteVerification
from voting.analytics import VoteAnalytics, TurnoutAnalytics, ComparisonAnalytics
from voting.exports import CSVExporter, ExcelExporter, PDFExporter, JSONExporter

User = get_user_model()


@pytest.mark.django_db
class TestVoteAnalytics(TestCase):
    """Test VoteAnalytics functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        # Create voters
        self.voters = []
        for i in range(5):
            voter = User.objects.create_user(
                email=f'voter{i}@test.com',
                password='testpass123',
                first_name=f'Voter{i}',
                last_name='Test',
                status='approved',
                role='voter'
            )
            VoterProfile.objects.create(
                user=voter,
                date_of_birth=timezone.now().date() - timedelta(days=365*25)
            )
            self.voters.append(voter)
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            scheduled_start=timezone.now() - timedelta(hours=2),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        # Create positions
        self.position1 = Position.objects.create(
            election=self.election,
            title='President',
            description='President position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=1
        )
        
        self.position2 = Position.objects.create(
            election=self.election,
            title='Vice President',
            description='VP position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=2
        )
        
        # Create candidates
        self.candidate1 = Candidate.objects.create(
            position=self.position1,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='approved',
            display_order=1
        )
        
        self.candidate2 = Candidate.objects.create(
            position=self.position1,
            first_name='Jane',
            last_name='Smith',
            email='jane@test.com',
            status='approved',
            display_order=2
        )
        
        self.candidate3 = Candidate.objects.create(
            position=self.position2,
            first_name='Bob',
            last_name='Johnson',
            email='bob@test.com',
            status='approved',
            display_order=1
        )
        
        # Register voters
        for voter in self.voters:
            ElectionVoter.objects.create(
                election=self.election,
                voter=voter,
                status='eligible'
            )
        
        # Create some votes (3 out of 5 voters)
        self.votes = []
        for i, voter in enumerate(self.voters[:3]):
            vote_data = {
                str(self.position1.id): [str(self.candidate1.id if i % 2 == 0 else self.candidate2.id)],
                str(self.position2.id): [str(self.candidate3.id)]
            }
            
            vote = Vote.objects.create(
                election=self.election,
                voter=voter,
                vote_data=vote_data
            )
            self.votes.append(vote)
    
    def test_get_total_votes(self):
        """Test counting total votes"""
        analytics = VoteAnalytics(self.election)
        total = analytics.get_total_votes()
        self.assertEqual(total, 3)
    
    def test_get_eligible_voters(self):
        """Test counting eligible voters"""
        analytics = VoteAnalytics(self.election)
        eligible = analytics.get_eligible_voters()
        self.assertEqual(eligible, 5)
    
    def test_get_turnout_percentage(self):
        """Test turnout calculation"""
        analytics = VoteAnalytics(self.election)
        turnout = analytics.get_turnout_percentage()
        self.assertEqual(turnout, 60.0)  # 3 out of 5 = 60%
    
    def test_get_position_statistics(self):
        """Test position statistics"""
        analytics = VoteAnalytics(self.election)
        stats = analytics.get_position_statistics()
        
        self.assertEqual(len(stats), 2)
        
        # Check President position
        pres = next(p for p in stats if p['position_title'] == 'President')
        self.assertEqual(pres['total_votes'], 3)
        self.assertEqual(len(pres['candidates']), 2)
        
        # Find winner (candidate1 got 2 votes, candidate2 got 1)
        winner = next(c for c in pres['candidates'] if c['rank'] == 1)
        self.assertEqual(winner['votes'], 2)
    
    def test_get_votes_by_hour(self):
        """Test hourly vote distribution"""
        analytics = VoteAnalytics(self.election)
        hourly = analytics.get_votes_by_hour()
        
        self.assertIsInstance(hourly, dict)
        self.assertTrue(len(hourly) > 0)
    
    def test_get_summary_statistics(self):
        """Test summary statistics"""
        analytics = VoteAnalytics(self.election)
        summary = analytics.get_summary_statistics()
        
        self.assertEqual(summary['total_votes'], 3)
        self.assertEqual(summary['eligible_voters'], 5)
        self.assertEqual(summary['turnout_percentage'], 60.0)
    
    def test_get_complete_report(self):
        """Test complete report generation"""
        analytics = VoteAnalytics(self.election)
        report = analytics.get_complete_report()
        
        self.assertIn('summary', report)
        self.assertIn('positions', report)
        self.assertIn('turnout_analysis', report)
        self.assertEqual(report['summary']['total_votes'], 3)


@pytest.mark.django_db
class TestTurnoutAnalytics(TestCase):
    """Test TurnoutAnalytics functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Reuse similar setup from TestVoteAnalytics
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            scheduled_start=timezone.now() - timedelta(hours=4),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        # Create position and candidate
        position = Position.objects.create(
            election=self.election,
            title='President',
            description='President position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=1
        )
        
        candidate = Candidate.objects.create(
            position=position,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='approved',
            display_order=1
        )
        
        # Create votes at different times
        for i in range(5):
            voter = User.objects.create_user(
                email=f'voter{i}@test.com',
                password='testpass123',
                first_name=f'Voter{i}',
                last_name='Test',
                status='approved',
                role='voter'
            )
            
            VoterProfile.objects.create(
                user=voter,
                date_of_birth=timezone.now().date() - timedelta(days=365*25)
            )
            
            ElectionVoter.objects.create(
                election=self.election,
                voter=voter,
                status='eligible'
            )
            
            # Create vote with staggered times
            vote = Vote.objects.create(
                election=self.election,
                voter=voter,
                vote_data={str(position.id): [str(candidate.id)]}
            )
            vote.cast_at = timezone.now() - timedelta(hours=4-i)
            vote.save()
    
    def test_get_turnout_trend(self):
        """Test turnout trend analysis"""
        trends = TurnoutAnalytics.get_turnout_trend(self.election)
        
        self.assertIsInstance(trends, list)
        self.assertTrue(len(trends) > 0)
        
        # Check trend data structure
        for trend in trends:
            self.assertIn('hour', trend)
            self.assertIn('cumulative_votes', trend)
            self.assertIn('cumulative_percentage', trend)
    
    def test_get_peak_voting_times(self):
        """Test peak voting times identification"""
        peaks = TurnoutAnalytics.get_peak_voting_times(self.election)
        
        self.assertIsInstance(peaks, list)
        # Should have at least one peak
        self.assertTrue(len(peaks) > 0)


@pytest.mark.django_db
class TestAnalyticsAPI(TestCase):
    """Test Analytics API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        
        # Create users
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.voter = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Voter',
            last_name='Test',
            status='approved',
            role='voter'
        )
        
        VoterProfile.objects.create(
            user=self.voter,
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='results_published',
            scheduled_start=timezone.now() - timedelta(hours=4),
            scheduled_end=timezone.now() - timedelta(hours=1),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        # Create position and candidates
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            description='President position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=1
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='approved',
            display_order=1
        )
        
        # Register voter and create vote
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter,
            status='voted'
        )
        
        Vote.objects.create(
            election=self.election,
            voter=self.voter,
            vote_data={str(self.position.id): [str(self.candidate.id)]}
        )
    
    def test_complete_report_api(self):
        """Test complete report endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/complete_report/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('positions', response.data)
    
    def test_summary_api(self):
        """Test summary endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/summary/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_votes', response.data)
        self.assertIn('turnout_percentage', response.data)
    
    def test_position_results_api(self):
        """Test position results endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/position_results/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
    
    def test_turnout_trend_api(self):
        """Test turnout trend endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/turnout_trend/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_dashboard_api(self):
        """Test dashboard endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get('/api/voting/analytics/dashboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('active_elections', response.data)
        self.assertIn('total_votes_today', response.data)
    
    def test_visualization_data_api(self):
        """Test visualization data endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/visualization_data/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access sensitive analytics"""
        # Unauthenticated request
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/complete_report/'
        )
        
        # Should allow access if results are published
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Change election to ongoing
        self.election.status = 'ongoing'
        self.election.save()
        
        # Should deny access to ongoing election
        response = self.client.get(
            f'/api/voting/analytics/{self.election.id}/complete_report/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestExports(TestCase):
    """Test export functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='completed',
            scheduled_start=timezone.now() - timedelta(hours=4),
            scheduled_end=timezone.now() - timedelta(hours=1),
            created_by=self.admin,
            modified_by=self.admin
        )
        
        position = Position.objects.create(
            election=self.election,
            title='President',
            description='President position',
            seats_available=1,
            candidates_per_voter=1,
            display_order=1
        )
        
        candidate = Candidate.objects.create(
            position=position,
            first_name='John',
            last_name='Doe',
            email='john@test.com',
            status='approved',
            display_order=1
        )
        
        voter = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Voter',
            last_name='Test',
            status='approved',
            role='voter'
        )
        
        VoterProfile.objects.create(
            user=voter,
            date_of_birth=timezone.now().date() - timedelta(days=365*25)
        )
        
        ElectionVoter.objects.create(
            election=self.election,
            voter=voter,
            status='voted'
        )
        
        Vote.objects.create(
            election=self.election,
            voter=voter,
            vote_data={str(position.id): [str(candidate.id)]}
        )
    
    def test_csv_export(self):
        """Test CSV export"""
        response = CSVExporter.export_results(self.election)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_json_export(self):
        """Test JSON export"""
        response = JSONExporter.export_complete_report(self.election)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Verify JSON content
        data = json.loads(response.content)
        self.assertIn('summary', data)
        self.assertIn('positions', data)


@pytest.mark.django_db
class TestExportAPI(TestCase):
    """Test Export API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            status='approved',
            role='admin'
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='completed',
            scheduled_start=timezone.now() - timedelta(hours=4),
            scheduled_end=timezone.now() - timedelta(hours=1),
            created_by=self.admin,
            modified_by=self.admin
        )
    
    def test_csv_export_api(self):
        """Test CSV export endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/exports/{self.election.id}/csv/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_json_export_api(self):
        """Test JSON export endpoint"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get(
            f'/api/voting/exports/{self.election.id}/json/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
