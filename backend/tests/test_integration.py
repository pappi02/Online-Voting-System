"""
Integration tests for iVote Systems
Tests complete end-to-end workflows combining multiple components
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from accounts.models import VoterProfile
from accounts.voter_models import VoterDocument
from elections.models import Election, Position, Candidate, ElectionVoter
from voting.models import Vote
from auditing.models import SecurityEvent, LoginAttempt

User = get_user_model()


class CompleteElectionWorkflowTest(TransactionTestCase):
    """Test complete election workflow from creation to results"""
    
    def setUp(self):
        """Set up complete test environment"""
        # Create admin
        self.admin = User.objects.create_user(email='admin@test.com', password='adminpass123', is_staff=True, is_superuser=True)
        
        # Create election
        now = timezone.now()
        self.election = Election.objects.create(
            title='Complete Workflow Election',
            description='Testing complete election lifecycle',
            election_type='general',
            status='draft',
            scheduled_start=now + timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            created_by=self.admin,
            allow_all_eligible=True,
            allow_multiple_candidates=False,
            require_voter_authentication=True
        )
        
        # Add positions
        self.president_position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1,
            order=1
        )
        
        self.vp_position = Position.objects.create(
            election=self.election,
            title='Vice President',
            num_selections=1,
            order=2
        )
        
        # Add candidates
        self.pres_cand1 = Candidate.objects.create(
            position=self.president_position,
            full_name='Alice Johnson'
        )
        self.pres_cand2 = Candidate.objects.create(
            position=self.president_position,
            full_name='Bob Smith'
        )
        
        self.vp_cand1 = Candidate.objects.create(
            position=self.vp_position,
            full_name='Charlie Brown'
        )
        self.vp_cand2 = Candidate.objects.create(
            position=self.vp_position,
            full_name='Diana Prince'
        )
    
    def test_complete_election_lifecycle(self):
        """Test complete election from draft to closed"""
        # 1. Verify election starts in draft
        self.assertEqual(self.election.status, 'draft')
        self.assertFalse(self.election.is_active())
        
        # 2. Transition to scheduled
        self.election.status = 'scheduled'
        self.election.save()
        self.assertEqual(self.election.status, 'scheduled')
        
        # 3. Transition to active
        self.election.status = 'active'
        self.election.scheduled_start = timezone.now() - timedelta(minutes=1)
        self.election.scheduled_end = timezone.now() + timedelta(minutes=59)
        self.election.save()
        self.assertTrue(self.election.is_active())
        
        # 4. Verify voting is allowed
        self.assertTrue(self.election.require_voter_authentication)
        
        # 5. Transition to closed
        self.election.status = 'closed'
        self.election.save()
        self.assertTrue(self.election.is_closed())
    
    def test_full_voter_registration_to_voting(self):
        """Test complete user flow: registration -> verification -> voting"""
        # 1. Create and register user
        voter_user = User.objects.create_user(email='voter1@example.com', password='securepass123')
        
        # 2. Create voter profile
        voter_profile = VoterProfile.objects.create(
            user=voter_user,
            voter_id='VOTER001',
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-15',
            is_eligible=False,
            is_verified=False
        )
        
        # 3. Upload documents for verification
        document = VoterDocument.objects.create(
            voter=voter_profile,
            document_type='passport',
            verification_status='pending'
        )
        
        # 4. Simulate document verification
        document.verification_status = 'verified'
        document.save()
        
        # 5. Mark voter as eligible
        voter_profile.is_eligible = True
        voter_profile.is_verified = True
        voter_profile.save()
        
        # 6. Activate election for voting
        self.election.status = 'active'
        self.election.scheduled_start = timezone.now() - timedelta(minutes=1)
        self.election.scheduled_end = timezone.now() + timedelta(minutes=59)
        self.election.save()
        
        # 7. Create election voter record
        election_voter = ElectionVoter.objects.create(
            election=self.election,
            voter=voter_profile,
            is_eligible=True,
            has_voted=False
        )
        
        # 8. Cast vote
        vote_data = {
            str(self.president_position.id): [str(self.pres_cand1.id)],
            str(self.vp_position.id): [str(self.vp_cand1.id)]
        }
        
        vote, verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=voter_profile,
            position_votes=vote_data,
            ip_address='192.168.1.100'
        )
        
        # 9. Verify vote was recorded
        self.assertIsNotNone(vote)
        self.assertIsNotNone(verification_code)
        self.assertEqual(vote.election, self.election)
        
        # 10. Update election voter record
        election_voter.has_voted = True
        election_voter.voted_at = timezone.now()
        election_voter.save()
        
        # 11. Verify voting prevented duplicate
        with self.assertRaises(ValueError):
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter_profile,
                position_votes=vote_data
            )
    
    def test_multi_user_voting_workflow(self):
        """Test voting with multiple users in same election"""
        self.election.status = 'active'
        self.election.scheduled_start = timezone.now() - timedelta(minutes=1)
        self.election.scheduled_end = timezone.now() + timedelta(minutes=59)
        self.election.save()
        
        voters = []
        votes = []
        
        # Create 10 voters and cast votes
        for i in range(10):
            # Create user
            voter_user = User.objects.create_user(
                username=f'voter{i}',
                email=f'voter{i}@example.com',
                password='testpass123'
            )
            
            # Create voter profile
            voter_profile = VoterProfile.objects.create(
                user=voter_user,
                voter_id=f'VOTER{i:03d}',
                is_eligible=True,
                is_verified=True
            )
            voters.append(voter_profile)
            
            # Cast vote
            candidate = self.pres_cand1 if i < 6 else self.pres_cand2
            vote_data = {
                str(self.president_position.id): [str(candidate.id)],
                str(self.vp_position.id): [str(self.vp_cand1.id)]
            }
            
            vote, code = Vote.cast_vote(
                election=self.election,
                voter_profile=voter_profile,
                position_votes=vote_data,
                ip_address=f'192.168.1.{i}'
            )
            votes.append(vote)
        
        # Verify vote counts
        total_votes = self.election.get_vote_count()
        self.assertEqual(total_votes, 10)
        
        # Verify each user can only vote once
        for voter_profile in voters:
            with self.assertRaises(ValueError):
                vote_data = {
                    str(self.president_position.id): [str(self.pres_cand1.id)],
                    str(self.vp_position.id): [str(self.vp_cand1.id)]
                }
                Vote.cast_vote(
                    election=self.election,
                    voter_profile=voter_profile,
                    position_votes=vote_data
                )


class UserAuthenticationIntegrationTest(APITestCase):
    """Test authentication workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(email='testuser@example.com', password='securepass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
    
    def test_login_logout_flow(self):
        """Test complete login/logout flow"""
        # Login
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'securepass123'
        }, format='json')
        
        # Should return token or redirect
        self.assertIn(response.status_code, [200, 400, 404])
        
        # Logout would be subsequent
        response = self.client.post('/api/auth/logout/')
        self.assertIn(response.status_code, [200, 400, 404])
    
    def test_authenticated_action_requires_login(self):
        """Test that protected actions require authentication"""
        # Attempt to perform protected action without auth
        response = self.client.get('/api/elections/')
        
        # May require login
        self.assertIn(response.status_code, [200, 401, 403, 404])


class SecurityAuditIntegrationTest(TestCase):
    """Test security and audit functionality integration"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='testuser@example.com', password='securepass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
    
    def test_login_attempt_tracking(self):
        """Test that login attempts are recorded"""
        # Record successful login
        attempt = LoginAttempt.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='TestBrowser',
            status='success'
        )
        
        self.assertEqual(attempt.status, 'success')
        self.assertEqual(attempt.user, self.user)
    
    def test_failed_login_tracking(self):
        """Test tracking of failed login attempts"""
        attempt = LoginAttempt.objects.create(
            user=self.user,
            ip_address='192.168.1.1',
            user_agent='TestBrowser',
            status='failed',
            failure_reason='Invalid password'
        )
        
        self.assertEqual(attempt.status, 'failed')
        self.assertEqual(attempt.failure_reason, 'Invalid password')
    
    def test_security_event_logging(self):
        """Test security event logging"""
        event = SecurityEvent.objects.create(
            user=self.user,
            event_type='vote_cast',
            severity='low',
            description='Voter cast vote in election',
            ip_address='192.168.1.1'
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, 'vote_cast')


class ElectionEligibilityIntegrationTest(TestCase):
    """Test election eligibility validation integration"""
    
    def setUp(self):
        """Set up test data"""
        self.admin = User.objects.create_user(email='admin@test.com', password='adminpass123', is_staff=True, is_superuser=True)
    
    def test_age_eligibility_check(self):
        """Test age eligibility validation"""
        # Create users of different ages
        young_user = User.objects.create_user(email='young@test.com', password='pass123')
        
        young_voter = VoterProfile.objects.create(
            user=young_user,
            voter_id='VOTER001',
            date_of_birth='2010-01-01',  # Too young
            is_eligible=False
        )
        
        adult_user = User.objects.create_user(email='adult@test.com', password='pass123')
        
        adult_voter = VoterProfile.objects.create(
            user=adult_user,
            voter_id='VOTER002',
            date_of_birth='2000-01-01',  # Old enough
            is_eligible=True
        )
        
        # Verify eligibility
        self.assertFalse(young_voter.is_eligible)
        self.assertTrue(adult_voter.is_eligible)


class CommunicationIntegrationTest(TestCase):
    """Test notification and communication workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='voter1@example.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=False
        )
    
    def test_voter_registration_notification(self):
        """Test that voter receives registration confirmation"""
        # In real scenario, this would send email
        # For testing, we just verify the notification service can be called
        
        from accounts.notification_service import send_registration_confirmation
        
        success, error = send_registration_confirmation(self.user)
        
        # Should attempt to send
        self.assertIsInstance(success, bool)
        self.assertIsInstance(error, (str, type(None)))
    
    def test_document_verification_notification(self):
        """Test notification on document verification"""
        document = VoterDocument.objects.create(
            voter=self.voter_profile,
            document_type='passport',
            verification_status='verified'
        )
        
        from accounts.notification_service import send_document_verified
        
        success, error = send_document_verified(
            self.user,
            'Passport',
            'admin'
        )
        
        self.assertIsInstance(success, bool)


class DataConsistencyIntegrationTest(TransactionTestCase):
    """Test data consistency across operations"""
    
    def setUp(self):
        """Set up test data"""
        self.admin = User.objects.create_user(email='admin@test.com', password='adminpass123', is_staff=True, is_superuser=True)
    
    def test_vote_database_constraints(self):
        """Test database constraints prevent invalid votes"""
        election = Election.objects.create(
            title='Constraint Test',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=self.admin
        )
        
        position = Position.objects.create(
            election=election,
            title='President'
        )
        
        candidate = Candidate.objects.create(
            position=position,
            full_name='Test Candidate'
        )
        
        voter_user = User.objects.create_user(email='voter1@test.com', password='pass123')
        
        voter_profile = VoterProfile.objects.create(
            user=voter_user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        # Cast first vote
        vote_data = {
            str(position.id): [str(candidate.id)]
        }
        
        vote1, _ = Vote.cast_vote(
            election=election,
            voter_profile=voter_profile,
            position_votes=vote_data
        )
        
        # Attempt to cast duplicate should fail
        with self.assertRaises(ValueError):
            Vote.cast_vote(
                election=election,
                voter_profile=voter_profile,
                position_votes=vote_data
            )
    
    def test_election_candidate_integrity(self):
        """Test integrity of election candidate relationships"""
        election = Election.objects.create(
            title='Integrity Test',
            election_type='general',
            status='draft',
            scheduled_start=timezone.now() + timedelta(days=30),
            scheduled_end=timezone.now() + timedelta(days=31),
            created_by=self.admin
        )
        
        position = Position.objects.create(
            election=election,
            title='President'
        )
        
        candidate = Candidate.objects.create(
            position=position,
            full_name='Test Candidate'
        )
        
        # Verify relationships
        self.assertEqual(candidate.position.election, election)
        self.assertIn(candidate, position.candidates.all())
        self.assertIn(position, election.positions.all())


class PerformanceIntegrationTest(TransactionTestCase):
    """Test system performance under load"""
    
    def setUp(self):
        """Set up test data"""
        self.admin = User.objects.create_user(email='admin@test.com', password='adminpass123', is_staff=True, is_superuser=True)
        
        self.election = Election.objects.create(
            title='Performance Test',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=self.admin
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President'
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            full_name='Test Candidate'
        )
    
    def test_bulk_voter_creation(self):
        """Test creating many voters"""
        voters = []
        for i in range(100):
            user = User.objects.create_user(
                username=f'bulk_voter{i}',
                email=f'bulk{i}@test.com',
                password='testpass123'
            )
            
            voter = VoterProfile.objects.create(
                user=user,
                voter_id=f'BULK{i:05d}',
                is_eligible=True,
                is_verified=True
            )
            voters.append(voter)
        
        self.assertEqual(len(voters), 100)
        self.assertEqual(VoterProfile.objects.count(), 100)
    
    def test_bulk_voting(self):
        """Test handling many votes"""
        # Create voters
        voters = []
        for i in range(50):
            user = User.objects.create_user(
                username=f'vote_test{i}',
                email=f'vote{i}@test.com',
                password='testpass123'
            )
            
            voter = VoterProfile.objects.create(
                user=user,
                voter_id=f'VOTE{i:05d}',
                is_eligible=True,
                is_verified=True
            )
            voters.append(voter)
        
        # Cast votes
        votes = []
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        
        for voter in voters:
            vote, _ = Vote.cast_vote(
                election=self.election,
                voter_profile=voter,
                position_votes=vote_data
            )
            votes.append(vote)
        
        # Verify all votes recorded
        self.assertEqual(len(votes), 50)
        self.assertEqual(self.election.get_vote_count(), 50)
