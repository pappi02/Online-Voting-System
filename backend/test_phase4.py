"""
Test Suite for Phase 4: Voting System
Tests vote casting, encryption, verification, and results
"""

import os
import sys
import django
import json

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ivs_backend.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, VoterProfile, EligibilityRule
from elections.models import Election, Position, Candidate, ElectionVoter, ElectionSchedule
from voting.models import Vote, VoteAudit, VoteVerification
from voting.encryption import vote_encryptor, verification_generator


class VoteEncryptionTest(TestCase):
    """Test vote encryption and decryption"""
    
    def test_encryption_decryption(self):
        """Test that vote data can be encrypted and decrypted"""
        # Create test data
        vote_data = {
            'position_1': ['candidate_1', 'candidate_2'],
            'position_2': ['candidate_3']
        }
        vote_json = json.dumps(vote_data
        )
        
        # Encrypt
        encrypted, iv = vote_encryptor.encrypt_vote(vote_json
        )
        
        # Verify encrypted data is different
        self.assertNotEqual(encrypted, vote_json
        )
        self.assertTrue(len(encrypted) > 0
        )
        self.assertTrue(len(iv) > 0
        )
        
        # Decrypt
        decrypted = vote_encryptor.decrypt_vote(encrypted, iv
        )
        decrypted_data = json.loads(decrypted
        )
        
        # Verify match
        self.assertEqual(decrypted_data, vote_data
        )
    
    def test_voter_hash_uniqueness(self):
        """Test that voter hashes are unique per election"""
        voter_id = "test-voter-123"
        election_id_1 = "election-1"
        election_id_2 = "election-2"
        
        # Generate hashes
        hash_1 = vote_encryptor.hash_voter_id(voter_id, election_id_1
        )
        hash_2 = vote_encryptor.hash_voter_id(voter_id, election_id_2
        )
        hash_1_duplicate = vote_encryptor.hash_voter_id(voter_id, election_id_1
        )
        
        # Verify properties
        self.assertEqual(len(hash_1), 64)  # SHA-256 produces 64 hex characters
        self.assertNotEqual(hash_1, hash_2)  # Different elections = different hashes
        self.assertEqual(hash_1, hash_1_duplicate)  # Same input = same hash
    
    def test_verification_code_generation(self):
        """Test verification code generation"""
        vote_id = "test-vote-123"
        timestamp = timezone.now().isoformat()
        
        # Generate code
        code = verification_generator.generate_code(vote_id, timestamp)
        
        # Verify format (ABC-DEF-GHI-JKL)
        self.assertTrue(verification_generator.validate_code_format(code))
        self.assertEqual(len(code), 15)  # 12 chars + 3 hyphens
        self.assertEqual(code.count('-'), 3)
        
        # Verify uniqueness (different inputs)
        code2 = verification_generator.generate_code(vote_id + "x", timestamp)
        self.assertNotEqual(code, code2)


class VoteModelsTest(TransactionTestCase):
    """Test Vote models"""
    
    def setUp(self):
        """Create test data"""
        # Create user
        self.user = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Voter',
            status='approved',
            role='voter'
        
        )
        
        # Create voter profile
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            verification_status='verified')
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            created_by=self.user,
            scheduled_start=timezone.now() - timedelta(hours=2),
            scheduled_end=timezone.now() + timedelta(days=7))
        
        # Create position
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            description='Presidential position',
            candidates_per_voter=1,
            display_order=1)
        
        # Create candidates
        self.candidate_1 = Candidate.objects.create(
            position=self.position,
            name='Candidate One',
            party='Party A',
            status='approved'
        
        )
        self.candidate_2 = Candidate.objects.create(
            position=self.position,
            name='Candidate Two',
            party='Party B',
            status='approved'
        
        )
        
        # Add voter to election
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter_profile,
            status='eligible'
        
        )
    
    def test_vote_casting(self):
        """Test casting a vote"""
        position_votes = {
            str(self.position.id): [str(self.candidate_1.id)]
        }
        
        # Cast vote
        vote, verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=position_votes,
            ip_address='127.0.0.1'
        
        )
        
        # Verify vote was created
        self.assertIsNotNone(vote.id
        )
        self.assertEqual(vote.election, self.election
        )
        self.assertTrue(len(verification_code) == 15
        )
        self.assertTrue(len(vote.encrypted_vote) > 0
        )
        self.assertTrue(len(vote.voter_hash) == 64
        )
        
        # Verify ElectionVoter status updated
        election_voter = ElectionVoter.objects.get(
            election=self.election,
            voter=self.voter_profile
        
        )
        self.assertEqual(election_voter.status, 'voted'
        )
    
    def test_duplicate_vote_prevention(self):
        """Test that duplicate voting is prevented"""
        position_votes = {
            str(self.position.id): [str(self.candidate_1.id)]
        }
        
        # Cast first vote
        Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=position_votes
        
        )
        
        # Try to vote again
        with self.assertRaises(ValueError) as context:
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=position_votes
            
        )
        
        self.assertIn('already cast', str(context.exception))
    def test_vote_decryption(self):
        """Test vote decryption"""
        position_votes = {
            str(self.position.id): [str(self.candidate_1.id)]
        }
        
        # Cast vote
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=position_votes
        
        )
        
        # Decrypt and verify
        decrypted_data = vote.decrypt_vote_data()
        self.assertEqual(decrypted_data, position_votes
        )
    
    def test_vote_verification(self):
        """Test vote verification"""
        position_votes = {
            str(self.position.id): [str(self.candidate_1.id)]
        }
        
        # Cast vote
        vote, verification_code = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=position_votes
        
        )
        
        # Verify vote
        success, retrieved_vote, message = VoteVerification.attempt_verification(
            verification_code,
            ip_address='127.0.0.1'
        
        )
        
        self.assertTrue(success)
        self.assertEqual(retrieved_vote.id, vote.id)
        self.assertIn('success', message.lower())
        # Check verification was logged
        self.assertIsNotNone(vote.verified_at)
    
    def test_invalid_verification_code(self):
        """Test verification with invalid code"""
        success, vote, message = VoteVerification.attempt_verification(
            'INVALID-CODE-XXX',
            ip_address='127.0.0.1'
        
        )
        
        self.assertFalse(success)
        self.assertIsNone(vote
        )
        self.assertIn('not found', message.lower())
    def test_audit_logging(self):
        """Test that voting actions are logged"""
        position_votes = {
            str(self.position.id): [str(self.candidate_1.id)]
        }
        
        # Cast vote
        vote, _ = Vote.cast_vote(
            election=self.election,
            voter_profile=self.voter_profile,
            position_votes=position_votes
        
        )
        
        # Check audit log created
        audit_logs = VoteAudit.objects.filter(
            action='vote_cast',
            vote=vote
        
        )
        self.assertEqual(audit_logs.count(), 1
        )
        
        # Verify vote
        vote.verify()
        
        # Check verification logged
        verification_logs = VoteAudit.objects.filter(
            action='vote_verified',
            vote=vote
        
        )
        self.assertEqual(verification_logs.count(), 1
        )


class VoteValidationTest(TransactionTestCase):
    """Test vote validation logic"""
    
    def setUp(self):
        """Create test data"""
        # Create user
        self.user = User.objects.create_user(
            email='voter@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Voter',
            status='approved',
            role='voter'
        
        )
        
        # Create voter profile
        self.voter_profile = VoterProfile.objects.create(
            user=self.user,
            verification_status='verified'
        
        )
        
        # Create election
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            created_by=self.user,
            scheduled_start=timezone.now() - timedelta(hours=2),
            scheduled_end=timezone.now() + timedelta(days=7))
        
        # Create position (allows 2 candidates)
        self.position = Position.objects.create(
            election=self.election,
            title='Board Member',
            description='Board position',
            candidates_per_voter=2,
            display_order=1
        
        )
        
        # Create candidates
        self.candidate_1 = Candidate.objects.create(
            position=self.position,
            name='Candidate One',
            party='Party A',
            status='approved'
        
        )
        self.candidate_2 = Candidate.objects.create(
            position=self.position,
            name='Candidate Two',
            party='Party B',
            status='approved'
        
        )
        self.candidate_3 = Candidate.objects.create(
            position=self.position,
            name='Candidate Three',
            party='Party C',
            status='approved'
        
        )
        
        # Add voter to election
        ElectionVoter.objects.create(
            election=self.election,
            voter=self.voter_profile,
            status='eligible'
        
        )
    
    def test_too_many_candidates_selected(self):
        """Test validation when too many candidates selected"""
        position_votes = {
            str(self.position.id): [
                str(self.candidate_1.id),
                str(self.candidate_2.id),
                str(self.candidate_3.id)  # 3 candidates for position allowing 2
            ]
        }
        
        with self.assertRaises(ValueError) as context:
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=position_votes
            
        )
        
        self.assertIn('Too many candidates', str(context.exception))
    def test_invalid_candidate(self):
        """Test validation with invalid candidate ID"""
        import uuid
        invalid_id = str(uuid.uuid4())
        
        position_votes = {
            str(self.position.id): [invalid_id]
        }
        
        with self.assertRaises(ValueError) as context:
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=position_votes
            
        )
        
        self.assertIn('Invalid candidate', str(context.exception))
    def test_unapproved_candidate(self):
        """Test validation with unapproved candidate"""
        # Create pending candidate
        pending_candidate = Candidate.objects.create(
            position=self.position,
            name='Pending Candidate',
            party='Party D',
            status='pending'
        
        )
        
        position_votes = {
            str(self.position.id): [str(pending_candidate.id)]
        }
        
        with self.assertRaises(ValueError) as context:
            Vote.cast_vote(
                election=self.election,
                voter_profile=self.voter_profile,
                position_votes=position_votes
            
        )
        
        self.assertIn('Invalid candidate', str(context.exception))
class ElectionResultsTest(TransactionTestCase):
    """Test election results calculation"""
    
    def setUp(self):
        """Create test data with multiple votes"""
        # Create election
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin',
            status='approved'
        
        )
        
        self.election = Election.objects.create(
            title='Test Election',
            description='Test Description',
            election_type='general',
            status='ongoing',
            created_by=self.admin,
            scheduled_start=timezone.now() - timedelta(hours=2),
            scheduled_end=timezone.now() + timedelta(days=7))
        
        # Create position
        self.position = Position.objects.create(
            election=self.election,
            title='President',
            description='Presidential position',
            candidates_per_voter=1,
            display_order=1
        
        )
        
        # Create candidates
        self.candidate_1 = Candidate.objects.create(
            position=self.position,
            name='Candidate One',
            party='Party A',
            status='approved'
        
        )
        self.candidate_2 = Candidate.objects.create(
            position=self.position,
            name='Candidate Two',
            party='Party B',
            status='approved'
        
        )
        
        # Create voters and cast votes
        for i in range(5):
            user = User.objects.create_user(
                email=f'voter{i}@test.com',
                password='testpass123',
                first_name=f'Voter{i}',
                last_name='Test',
                role='voter',
                status='approved'
            
        )
            
            voter_profile = VoterProfile.objects.create(
                user=user,
                verification_status='verified'
            
        )
            
            ElectionVoter.objects.create(
                election=self.election,
                voter=voter_profile,
                status='eligible')
            
            # Vote for candidate_1 (3 votes) or candidate_2 (2 votes)
            candidate = self.candidate_1 if i < 3 else self.candidate_2
            
            position_votes = {
                str(self.position.id): [str(candidate.id)]
            }
            
            Vote.cast_vote(
                election=self.election,
                voter_profile=voter_profile,
                position_votes=position_votes
            
        )
    
    def test_vote_counting(self):
        """Test that votes are counted correctly"""
        from voting.views import ElectionResultsViewSet
        
        # Create viewset instance
        viewset = ElectionResultsViewSet()
        
        # Calculate results
        results = viewset._calculate_results(self.election
        )
        
        # Verify structure
        self.assertEqual(results['total_votes'], 5
        )
        self.assertEqual(len(results['positions']), 1
        )
        
        # Get position results
        position_result = results['positions'][0]
        self.assertEqual(len(position_result['candidates']), 2
        )
        
        # Find candidate results
        candidate_results = {c['name']: c for c in position_result['candidates']}
        
        # Verify vote counts
        self.assertEqual(candidate_results['Candidate One']['votes'], 3
        )
        self.assertEqual(candidate_results['Candidate Two']['votes'], 2
        )
        
        # Verify percentages
        self.assertEqual(candidate_results['Candidate One']['percentage'], 60.0
        )
        self.assertEqual(candidate_results['Candidate Two']['percentage'], 40.0
        )
    
    def test_results_ordering(self):
        """Test that results are ordered by vote count"""
        from voting.views import ElectionResultsViewSet
        
        viewset = ElectionResultsViewSet()
        results = viewset._calculate_results(self.election)
        
        # Get candidates
        candidates = results['positions'][0]['candidates']
        
        # Verify ordering (descending by votes)
        self.assertEqual(candidates[0]['name'], 'Candidate One')  # 3 votes
        self.assertEqual(candidates[1]['name'], 'Candidate Two')  # 2 votes


def run_tests():
    """Run all tests"""
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings
        )
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False
        )
    
    # Run specific test classes
    failures = test_runner.run_tests([
        'test_phase4.VoteEncryptionTest',
        'test_phase4.VoteModelsTest',
        'test_phase4.VoteValidationTest',
        'test_phase4.ElectionResultsTest',
    ]
        )
    
    return failures


if __name__ == '__main__':
    print("\n" + "="*70
        )
    print("Phase 4: Voting System - Test Suite"
        )
    print("="*70 + "\n"
        )
    
    failures = run_tests()
    
    print("\n" + "="*70
        )
    if failures == 0:
        print("✓ All Phase 4 tests passed!"
        )
    else:
        print(f"✗ {failures} test(s) failed"
        )
    print("="*70 + "\n"
        )
    
    sys.exit(failures
        )
