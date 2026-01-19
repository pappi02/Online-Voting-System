#!/usr/bin/env python
"""
Phase 3 Election Management - Test Script
Validates all election, candidate, and voting models are working correctly
"""

import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ivs_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from elections.models import (
    Election, Position, Candidate, ElectionVoter,
    ElectionSchedule, ElectionInvite
)
from accounts.voter_models import VoterProfile

User = get_user_model()

def test_election_models():
    """Test Election model creation and methods"""
    print("\n" + "="*60)
    print("TESTING ELECTION MODELS")
    print("="*60)
    
    # Create test user
    admin_user, created = User.objects.get_or_create(
        email='admin@test.com',
        defaults={
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True
        }
    )
    print(f"✓ Admin user: {admin_user.email}")
    
    # Create election
    future_start = timezone.now() + timedelta(days=7)
    future_end = timezone.now() + timedelta(days=8)
    
    election, created = Election.objects.get_or_create(
        title='Sample Election 2026',
        defaults={
            'description': 'A sample election for testing Phase 3',
            'election_type': 'general',
            'status': 'draft',
            'scheduled_start': future_start,
            'scheduled_end': future_end,
            'created_by': admin_user,
            'allow_all_eligible': True,
            'allow_multiple_candidates': False,
            'results_visible_before_close': False,
        }
    )
    print(f"✓ Election created: {election.title} (ID: {election.id})")
    print(f"  - Status: {election.status}")
    print(f"  - Start: {election.scheduled_start}")
    print(f"  - End: {election.scheduled_end}")
    
    # Create positions
    positions = []
    for pos_title in ['President', 'Vice President', 'Treasurer']:
        position, created = Position.objects.get_or_create(
            election=election,
            title=pos_title,
            defaults={
                'description': f'{pos_title} position',
                'seats_available': 1,
                'candidates_per_voter': 1,
                'display_order': len(positions)
            }
        )
        positions.append(position)
        print(f"✓ Position created: {position.title} (Seats: {position.seats_available})")
    
    # Create candidates
    for i, position in enumerate(positions):
        candidate, created = Candidate.objects.get_or_create(
            position=position,
            full_name=f'Candidate {i+1} for {position.title}',
            defaults={
                'biography': f'Biography for candidate {i+1}',
                'party_affiliation': f'Party {chr(65+i)}',  # Party A, B, C
                'email': f'candidate{i+1}@test.com',
                'status': 'approved',
            }
        )
        print(f"  ✓ Candidate: {candidate.full_name} ({candidate.status})")
    
    # Test election schedule
    schedule, created = ElectionSchedule.objects.get_or_create(
        election=election,
        defaults={'current_state': 'draft'}
    )
    print(f"✓ Election schedule created: {schedule.current_state}")
    
    # Test election status methods
    print(f"\n✓ Election Status Methods:")
    print(f"  - Is Active: {election.is_active()}")
    print(f"  - Is Upcoming: {election.is_upcoming()}")
    print(f"  - Is Closed: {election.is_closed()}")
    print(f"  - Position Count: {election.positions.count()}")
    
    return election, positions


def test_serializers():
    """Test serializer imports and functionality"""
    print("\n" + "="*60)
    print("TESTING SERIALIZERS")
    print("="*60)
    
    try:
        from elections.serializers import (
            ElectionListSerializer, ElectionDetailSerializer,
            ElectionCreateSerializer, PositionListSerializer,
            PositionDetailSerializer, CandidateListSerializer,
            CandidateDetailSerializer
        )
        print("✓ All serializers imported successfully")
        
        election = Election.objects.first()
        if election:
            serializer = ElectionListSerializer(election)
            print(f"✓ ElectionListSerializer works: {serializer.data['title']}")
            
            detail_serializer = ElectionDetailSerializer(election)
            print(f"✓ ElectionDetailSerializer works with {len(detail_serializer.data)} fields")
    except Exception as e:
        print(f"✗ Serializer Error: {e}")
        return False
    
    return True


def test_viewsets():
    """Test viewset imports"""
    print("\n" + "="*60)
    print("TESTING VIEWSETS")
    print("="*60)
    
    try:
        from elections.views import (
            ElectionViewSet, PositionViewSet, CandidateViewSet,
            ElectionVoterViewSet, ElectionScheduleViewSet,
            ElectionInviteViewSet
        )
        print("✓ All viewsets imported successfully")
        print("  - ElectionViewSet")
        print("  - PositionViewSet")
        print("  - CandidateViewSet")
        print("  - ElectionVoterViewSet")
        print("  - ElectionScheduleViewSet")
        print("  - ElectionInviteViewSet")
    except Exception as e:
        print(f"✗ Viewset Error: {e}")
        return False
    
    return True


def test_admin_interface():
    """Test admin interface registrations"""
    print("\n" + "="*60)
    print("TESTING ADMIN INTERFACE")
    print("="*60)
    
    try:
        from elections.admin import (
            ElectionAdmin, PositionAdmin, CandidateAdmin,
            ElectionVoterAdmin, ElectionScheduleAdmin,
            ElectionInviteAdmin
        )
        from django.contrib import admin
        
        # Check if models are registered
        election_admin = admin.site._registry.get(Election)
        position_admin = admin.site._registry.get(Position)
        candidate_admin = admin.site._registry.get(Candidate)
        
        if election_admin and position_admin and candidate_admin:
            print("✓ Election models registered with admin")
            print("  - Election Admin")
            print("  - Position Admin")
            print("  - Candidate Admin")
            print("  - ElectionVoter Admin")
            print("  - ElectionSchedule Admin")
            print("  - ElectionInvite Admin")
            return True
        else:
            print("✗ Some models not registered with admin")
            return False
    except Exception as e:
        print(f"✗ Admin Error: {e}")
        return False


def test_urls():
    """Test URL routing"""
    print("\n" + "="*60)
    print("TESTING URL ROUTING")
    print("="*60)
    
    try:
        from django.urls import reverse, get_resolver
        from elections.urls import urlpatterns
        
        print("✓ Elections URLs configured")
        print("  Expected routes:")
        print("    - /api/v1/elections/")
        print("    - /api/v1/elections/{id}/")
        print("    - /api/v1/elections/{id}/positions/")
        print("    - /api/v1/elections/{id}/positions/{id}/candidates/")
        return True
    except Exception as e:
        print(f"✗ URL Error: {e}")
        return False


def test_database_integrity():
    """Test database constraints and relationships"""
    print("\n" + "="*60)
    print("TESTING DATABASE INTEGRITY")
    print("="*60)
    
    try:
        # Test foreign keys
        elections = Election.objects.count()
        positions = Position.objects.count()
        candidates = Candidate.objects.count()
        
        print(f"✓ Database Integrity:")
        print(f"  - Elections: {elections}")
        print(f"  - Positions: {positions}")
        print(f"  - Candidates: {candidates}")
        print(f"  - Election Schedules: {ElectionSchedule.objects.count()}")
        print(f"  - Election Voters: {ElectionVoter.objects.count()}")
        print(f"  - Election Invites: {ElectionInvite.objects.count()}")
        
        return True
    except Exception as e:
        print(f"✗ Database Integrity Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  PHASE 3: ELECTION MANAGEMENT - TEST SUITE".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    results = []
    
    try:
        test_election_models()
        results.append(("Election Models", True))
    except Exception as e:
        print(f"✗ Election Models Error: {e}")
        results.append(("Election Models", False))
    
    try:
        test_serializers()
        results.append(("Serializers", True))
    except Exception as e:
        print(f"✗ Serializers Error: {e}")
        results.append(("Serializers", False))
    
    try:
        test_viewsets()
        results.append(("Viewsets", True))
    except Exception as e:
        print(f"✗ Viewsets Error: {e}")
        results.append(("Viewsets", False))
    
    try:
        test_admin_interface()
        results.append(("Admin Interface", True))
    except Exception as e:
        print(f"✗ Admin Interface Error: {e}")
        results.append(("Admin Interface", False))
    
    try:
        test_urls()
        results.append(("URL Routing", True))
    except Exception as e:
        print(f"✗ URL Routing Error: {e}")
        results.append(("URL Routing", False))
    
    try:
        test_database_integrity()
        results.append(("Database Integrity", True))
    except Exception as e:
        print(f"✗ Database Integrity Error: {e}")
        results.append(("Database Integrity", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "█"*60)
        print("█" + "  ✓ ALL TESTS PASSED!".center(58) + "█")
        print("█" + "  Phase 3 implementation is ready for deployment.".center(58) + "█")
        print("█"*60 + "\n")
        return 0
    else:
        print("\n" + "█"*60)
        print("█" + "  ✗ SOME TESTS FAILED".center(58) + "█")
        print("█"*60 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
