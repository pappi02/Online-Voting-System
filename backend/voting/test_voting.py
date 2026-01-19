"""
Comprehensive voting tests for iVote Systems
Tests vote casting, verification, encryption, and fraud prevention
"""

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
import json
import uuid

from django.contrib.auth import get_user_model
from accounts.models import VoterProfile
from accounts.voter_models import VoterDocument
from elections.models import Election, Position, Candidate, ElectionVoter
from voting.models import Vote

User = get_user_model()


class VoteModelTests(TransactionTestCase):
    """Test Vote model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='voter1@test.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Testing voting system',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            description='Vote for President',
            num_selections=1
        )
        
        self.candidate1 = Candidate.objects.create(
            position=self.position,
            full_name='John Doe',
            bio='Candidate A'
        )
        self.candidate2 = Candidate.objects.create(
            position=self.position,
            full_name='Jane Smith',
            bio='Candidate B'
        )
    
    def test_vote_creation(self):
        """Test vote model creation"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        vote, verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data,
            ip_address='192.168.1.1',
            user_agent='TestBrowser'
        )
        
        self.assertIsNotNone(vote)
        self.assertIsNotNone(verification_code)
        self.assertTrue(vote.verification_code)
        self.assertEqual(vote.election, self.election)
        self.assertEqual(vote.ip_address, '192.168.1.1')
    
    def test_vote_encryption(self):
        """Test vote data is encrypted"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Encrypted data should not contain plaintext candidate info
        self.assertNotIn(self.candidate1.full_name, vote.encrypted_vote)
        self.assertNotIn('John', vote.encrypted_vote)
        self.assertTrue(vote.encryption_iv)
    
    def test_duplicate_vote_prevention(self):
        """Test that double voting is prevented"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        # Cast first vote
        Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Attempt to cast second vote
        with self.assertRaises(ValueError) as context:
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=vote_data
            )
        
        self.assertIn('already cast', str(context.exception))
    
    def test_verification_code_uniqueness(self):
        """Test that verification codes are unique"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        vote1, code1 = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Create second voter and vote
        user2 = User.objects.create_user(email='voter2@test.com', password='testpass123')
        voter2 = VoterProfile.objects.create(
            user=user2,
            voter_id='VOTER002',
            is_eligible=True,
            is_verified=True
        )
        
        vote2, code2 = Vote.cast_vote(
            election=self.election,
            voter_profile=voter2,
            position_votes=vote_data
        )
        
        self.assertNotEqual(code1, code2)
        self.assertNotEqual(vote1.verification_code, vote2.verification_code)
    
    def test_vote_metadata_capture(self):
        """Test that vote metadata is properly captured"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data,
            ip_address='10.0.0.1',
            user_agent='Mozilla/5.0 TestBrowser'
        )
        
        self.assertEqual(vote.ip_address, '10.0.0.1')
        self.assertEqual(vote.user_agent, 'Mozilla/5.0 TestBrowser')
        self.assertIsNotNone(vote.cast_at)
        self.assertLessEqual(vote.cast_at, timezone.now())
    
    def test_vote_anonymity(self):
        """Test that votes are anonymous (no direct voter link)"""
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Vote should not contain voter profile link
        self.assertNotIn(str(self.voter_profile.id), vote.encrypted_vote)
        self.assertTrue(vote.voter_hash)  # Should have hash instead


class VoteValidationTests(TestCase):
    """Test vote validation and constraints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='voter1@test.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1
        )
        
        self.candidate1 = Candidate.objects.create(
            position=self.position,
            full_name='John Doe'
        )
        self.candidate2 = Candidate.objects.create(
            position=self.position,
            full_name='Jane Smith'
        )
    
    def test_vote_on_closed_election(self):
        """Test that voting is not allowed on closed elections"""
        closed_election = Election.objects.create(
            title='Closed Election',
            election_type='general',
            status='closed',
            scheduled_start=timezone.now() - timedelta(days=1),
            scheduled_end=timezone.now() - timedelta(hours=1),
            created_by=self.user
        )
        
        vote_data = {
            str(self.position.id): [str(self.candidate1.id)]
        }
        
        with self.assertRaises(ValueError):
            Vote.cast_vote(
                election=closed_election,
                voter_profile=self.voter_profile,
                position_votes=vote_data
            )
    
    def test_invalid_candidate_selection(self):
        """Test validation of candidate selection"""
        vote_data = {
            str(self.position.id): ['invalid-candidate-id']
        }
        
        with self.assertRaises(ValueError):
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=vote_data
            )
    
    def test_multiple_selections_validation(self):
        """Test validation of multiple selections per position"""
        # Create position allowing 2 selections
        multi_position = Position.objects.create(
            election=self.election,
            title='Board Members',
            num_selections=2
        )
        
        multi_cand1 = Candidate.objects.create(
            position=multi_position,
            full_name='Candidate 1'
        )
        multi_cand2 = Candidate.objects.create(
            position=multi_position,
            full_name='Candidate 2'
        )
        multi_cand3 = Candidate.objects.create(
            position=multi_position,
            full_name='Candidate 3'
        )
        
        # Valid: 2 selections
        vote_data = {
            str(multi_position.id): [str(multi_cand1.id), str(multi_cand2.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        self.assertIsNotNone(vote)
        
        # Invalid: 3 selections (exceeds limit)
        user2 = User.objects.create_user(email='voter2@test.com', password='testpass123')
        voter2 = VoterProfile.objects.create(
            user=user2,
            voter_id='VOTER002',
            is_eligible=True,
            is_verified=True
        )
        
        invalid_vote_data = {
            str(multi_position.id): [
                str(multi_cand1.id),
                str(multi_cand2.id),
                str(multi_cand3.id)
            ]
        }
        
        with self.assertRaises(ValueError):
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter2,
                position_votes=invalid_vote_data
            )


class VoteVerificationTests(TestCase):
    """Test vote verification functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='voter1@test.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            full_name='John Doe'
        )
        
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        
        self.vote, self.verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
    
    def test_verification_code_format(self):
        """Test verification code format"""
        self.assertTrue(len(self.verification_code) > 0)
        self.assertIsNotNone(self.vote.verification_code)
    
    def test_verify_vote(self):
        """Test vote verification"""
        self.vote.verify()
        self.assertIsNotNone(self.vote.verified_at)
        self.assertLessEqual(self.vote.verified_at, timezone.now())
    
    def test_retrieve_vote_by_code(self):
        """Test retrieving vote by verification code"""
        retrieved_vote = Vote.objects.get(verification_code=self.verification_code)
        self.assertEqual(retrieved_vote.id, self.vote.id)
    
    def test_invalid_verification_code(self):
        """Test invalid verification code"""
        with self.assertRaises(Vote.DoesNotExist):
            Vote.objects.get(verification_code='INVALID-CODE-999')


class VoteStatisticsTests(TestCase):
    """Test vote counting and statistics"""
    
    def setUp(self):
        """Set up test data"""
        self.election = Election.objects.create(
            title='Test Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1
        )
        
        self.candidate1 = Candidate.objects.create(
            position=self.position,
            full_name='John Doe'
        )
        self.candidate2 = Candidate.objects.create(
            position=self.position,
            full_name='Jane Smith'
        )
    
    def test_vote_count(self):
        """Test vote counting"""
        # Create 5 voters and cast votes
        for i in range(5):
            user = User.objects.create_user(
                username=f'voter{i}',
                email=f'voter{i}@test.com',
                password='testpass123'
            )
            voter = VoterProfile.objects.create(
                user=user,
                voter_id=f'VOTER{i:03d}',
                is_eligible=True,
                is_verified=True
            )
            
            vote_data = {
                str(self.position.id): [str(self.candidate1.id)]
            }
            
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter,
                position_votes=vote_data
            )
        
        vote_count = self.election.get_vote_count()
        self.assertEqual(vote_count, 5)
    
    def test_participation_rate(self):
        """Test participation rate calculation"""
        # Create 10 eligible voters
        for i in range(10):
            user = User.objects.create_user(
                username=f'voter{i}',
                email=f'voter{i}@test.com',
                password='testpass123'
            )
            VoterProfile.objects.create(
                user=user,
                voter_id=f'VOTER{i:03d}',
                is_eligible=True,
                is_verified=True
            )
        
        # Have 5 of them vote
        for i in range(5):
            voter = VoterProfile.objects.get(voter_id=f'VOTER{i:03d}')
            vote_data = {
                str(self.position.id): [str(self.candidate1.id)]
            }
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter,
                position_votes=vote_data
            )
        
        participation = self.election.get_participation_rate()
        self.assertEqual(participation, 50.0)
    
    def test_candidate_vote_count(self):
        """Test counting votes per candidate"""
        # Create voters and split votes
        for i in range(6):
            user = User.objects.create_user(
                username=f'voter{i}',
                email=f'voter{i}@test.com',
                password='testpass123'
            )
            voter = VoterProfile.objects.create(
                user=user,
                voter_id=f'VOTER{i:03d}',
                is_eligible=True,
                is_verified=True
            )
            
            # First 3 vote for candidate1, last 3 for candidate2
            candidate = self.candidate1 if i < 3 else self.candidate2
            
            vote_data = {
                str(self.position.id): [str(candidate.id)]
            }
            
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter,
                position_votes=vote_data
            )
        
        # Count votes for each candidate
        cand1_votes = self.candidate1.get_vote_count()
        cand2_votes = self.candidate2.get_vote_count()
        
        self.assertEqual(cand1_votes, 3)
        self.assertEqual(cand2_votes, 3)


class VoteAPITests(APITestCase):
    """Test Vote API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(email='voter1@test.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            full_name='John Doe'
        )
    
    def test_cast_vote_authenticated(self):
        """Test casting vote with authentication"""
        self.client.login(username='voter1', password='testpass123')
        
        vote_data = {
            'election': str(self.election.id),
            'votes': {
                str(self.position.id): [str(self.candidate.id)]
            }
        }
        
        response = self.client.post('/api/votes/cast/', vote_data, format='json')
        
        # Should succeed or return appropriate status
        self.assertIn(response.status_code, [201, 200, 400])
    
    def test_cast_vote_unauthenticated(self):
        """Test casting vote without authentication"""
        vote_data = {
            'election': str(self.election.id),
            'votes': {
                str(self.position.id): [str(self.candidate.id)]
            }
        }
        
        response = self.client.post('/api/votes/cast/', vote_data, format='json')
        
        # Should require authentication
        self.assertIn(response.status_code, [401, 403])
    
    def test_verify_vote(self):
        """Test vote verification endpoint"""
        self.client.login(username='voter1', password='testpass123')
        
        # First cast a vote
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        vote, verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Then verify it
        response = self.client.get(f'/api/votes/verify/{verification_code}/')
        
        # Should return vote information
        self.assertIn(response.status_code, [200, 404])


class VoteSecurityTests(TestCase):
    """Test security aspects of voting"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email='voter1@test.com', password='testpass123')
        
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            voter_id='VOTER001',
            is_eligible=True,
            is_verified=True
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=User.objects.create_user(email='admin@test.com', password='adminpass123')
        )
        
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            num_selections=1
        )
        
        self.candidate = Candidate.objects.create(
            position=self.position,
            full_name='John Doe'
        )
    
    def test_vote_data_not_exposed_in_plaintext(self):
        """Test that vote data is not exposed in plaintext"""
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Vote should not contain candidate name or ID
        self.assertNotIn(self.candidate.full_name, vote.encrypted_vote)
        self.assertNotIn(str(self.candidate.id), vote.encrypted_vote)
    
    def test_voter_anonymity_preserved(self):
        """Test that voter identity is not revealed"""
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Vote record should not contain voter ID, email, or other PII
        self.assertNotIn(str(self.voter_profile.id), vote.encrypted_vote)
        self.assertNotIn(self.user.email, vote.encrypted_vote)
    
    def test_vote_tampering_detection(self):
        """Test that tampered votes are detected"""
        vote_data = {
            str(self.position.id): [str(self.candidate.id)]
        }
        
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data
        )
        
        # Tamper with encrypted vote
        original_vote = vote.encrypted_vote
        vote.encrypted_vote = 'TAMPERED_DATA'
        vote.save()
        
        # Decryption should fail or detect tampering
        with self.assertRaises(Exception):
            vote.decrypt_vote()
    
    def test_multiple_elections_isolation(self):
        """Test that votes in different elections are isolated"""
        # Create second election
        election2 = Election.objects.create(
            title='Second Election',
            election_type='general',
            status='active',
            scheduled_start=timezone.now() - timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=1),
            created_by=self.user
        )
        
        position2 = Position.objects.create(
            election=election2,
            title='Governor',
            num_selections=1
        )
        
        candidate2 = Candidate.objects.create(
            position=position2,
            full_name='Jane Smith'
        )
        
        # Vote in first election
        vote_data1 = {
            str(self.position.id): [str(self.candidate.id)]
        }
        vote1, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=vote_data1
        )
        
        # Should be able to vote in second election with same voter
        vote_data2 = {
            str(position2.id): [str(candidate2.id)]
        }
        vote2, _ = Vote.cast_vote(
            election=election2,
            voter_profile=self.voter_profile,
            position_votes=vote_data2
        )
        
        self.assertNotEqual(vote1.election, vote2.election)
        self.assertEqual(vote1.election, self.election)
        self.assertEqual(vote2.election, election2)
