"""
Voter registration and verification views
Handles voter profile management, document uploads, and eligibility checking
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.voter_models import (
    VoterProfile, VoterDocument, EligibilityRule, VerificationLog
)
from accounts.voter_serializers import (
    VoterProfileSerializer, VoterDocumentSerializer, VoterRegistrationSerializer,
    DocumentUploadSerializer, EligibilityRuleSerializer, VerificationLogSerializer
)
from accounts.permissions import IsAdmin
from accounts.utils import log_audit_event, get_client_ip, get_user_agent

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class VoterRegistrationView(generics.CreateAPIView):
    """
    Voter registration endpoint
    Handles complete voter registration with profile creation
    """
    serializer_class = VoterRegistrationSerializer
    permission_classes = [AllowAny]
    
    def perform_create(self, serializer):
        """Handle voter registration"""
        data = serializer.save()
        user = data['user']
        voter_profile = data['voter_profile']
        
        logger.info(f"New voter registered: {user.email}")
        
        # Log audit event
        log_audit_event(
            user=user,
            action='login',
            description='Voter account created',
            request=self.request,
            details={
                'registration_type': 'voter',
                'verification_status': voter_profile.verification_status
            }
        )
    
    def create(self, request, *args, **kwargs):
        """Override create to return custom response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(
            {
                'message': 'Voter registration successful',
                'email': serializer.validated_data['email'],
                'next_step': 'Please verify your email and upload required documents'
            },
            status=status.HTTP_201_CREATED
        )


class VoterProfileViewSet(viewsets.ModelViewSet):
    """
    Voter profile management
    """
    serializer_class = VoterProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Users can only see their own profile, admins can see all"""
        user = self.request.user
        if user.is_admin():
            return VoterProfile.objects.all()
        return VoterProfile.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's voter profile"""
        try:
            voter_profile = VoterProfile.objects.get(user=request.user)
            serializer = self.get_serializer(voter_profile)
            return Response(serializer.data)
        except VoterProfile.DoesNotExist:
            return Response(
                {'error': 'Voter profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['put', 'patch'])
    def update_profile(self, request, id=None):
        """Update voter profile"""
        voter_profile = self.get_object()
        
        serializer = self.get_serializer(
            voter_profile,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            
            # Log update
            log_audit_event(
                user=request.user,
                action='profile_updated',
                description='Voter profile updated',
                request=request,
                details=request.data
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def check_eligibility(self, request, id=None):
        """Check voter eligibility status"""
        voter_profile = self.get_object()
        is_eligible, reasons = voter_profile.validate_eligibility()
        
        return Response({
            'is_eligible': is_eligible,
            'eligibility_issues': reasons,
            'verification_status': voter_profile.verification_status,
            'age': voter_profile.calculate_age(),
            'documents_verified': voter_profile.documents.filter(
                verification_status='verified'
            ).count()
        })
    
    @action(detail=True, methods=['get'])
    def documents(self, request, id=None):
        """Get voter's documents"""
        voter_profile = self.get_object()
        documents = voter_profile.documents.all()
        serializer = VoterDocumentSerializer(documents, many=True)
        return Response(serializer.data)


class VoterDocumentViewSet(viewsets.ModelViewSet):
    """
    Voter document management
    Handles document uploads and verification
    """
    serializer_class = VoterDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    lookup_field = 'id'
    
    def get_queryset(self):
        """Users can only see their own documents, admins can see all"""
        user = self.request.user
        if user.is_admin():
            return VoterDocument.objects.all()
        
        try:
            voter_profile = VoterProfile.objects.get(user=user)
            return VoterDocument.objects.filter(voter=voter_profile)
        except VoterProfile.DoesNotExist:
            return VoterDocument.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Upload a voter document"""
        try:
            voter_profile = VoterProfile.objects.get(user=request.user)
        except VoterProfile.DoesNotExist:
            return Response(
                {'error': 'Voter profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            document = serializer.save(voter=voter_profile)
            
            logger.info(f"Document uploaded: {document.id} by {request.user.email}")
            
            # Log event
            log_audit_event(
                user=request.user,
                action='login',
                description=f'Document uploaded: {document.get_document_type_display()}',
                request=request
            )
            
            response_serializer = VoterDocumentSerializer(document)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def verify(self, request, id=None):
        """Verify a voter document (Admin only)"""
        document = self.get_object()
        action_type = request.data.get('action', 'verified')  # 'verified' or 'rejected'
        notes = request.data.get('notes', '')
        
        if action_type not in ['verified', 'rejected']:
            return Response(
                {'error': 'Invalid action'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document.verification_status = action_type
        document.verified_by = request.user
        document.verification_notes = notes
        document.verified_at = timezone.now()
        document.save()
        
        # Create verification log
        VerificationLog.objects.create(
            voter=document.voter,
            action=f'document_{action_type}',
            performed_by=request.user,
            description=f'{document.get_document_type_display()} {action_type}',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={'document_id': str(document.id), 'notes': notes}
        )
        
        logger.info(
            f"Document {action_type}: {document.id} by {request.user.email}"
        )
        
        return Response(
            VoterDocumentSerializer(document).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def bulk_verify(self, request):
        """Bulk verify documents (Admin only)"""
        document_ids = request.data.get('document_ids', [])
        action_type = request.data.get('action', 'verified')
        notes = request.data.get('notes', '')
        
        if not document_ids:
            return Response(
                {'error': 'No documents specified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        documents = VoterDocument.objects.filter(id__in=document_ids)
        updated_count = 0
        
        for document in documents:
            document.verification_status = action_type
            document.verified_by = request.user
            document.verification_notes = notes
            document.verified_at = timezone.now()
            document.save()
            
            # Create log
            VerificationLog.objects.create(
                voter=document.voter,
                action=f'document_{action_type}',
                performed_by=request.user,
                description=f'Bulk: {document.get_document_type_display()} {action_type}',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)
            )
            
            updated_count += 1
        
        return Response({
            'message': f'{updated_count} documents updated',
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)


class VerificationManagementViewSet(viewsets.ViewSet):
    """
    Verification management for admins
    View and manage voter verification status
    """
    permission_classes = [IsAdmin]
    
    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """Get voters pending verification"""
        voters = VoterProfile.objects.filter(
            verification_status='pending'
        ).select_related('user')
        
        serializer = VoterProfileSerializer(voters, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def verification_queue(self, request):
        """Get verification queue with document status"""
        voters = VoterProfile.objects.filter(
            verification_status__in=['pending', 'under_review']
        ).prefetch_related('documents')
        
        data = []
        for voter in voters:
            docs = voter.documents.all()
            pending_docs = docs.filter(verification_status='pending').count()
            verified_docs = docs.filter(verification_status='verified').count()
            
            data.append({
                'id': str(voter.id),
                'voter_email': voter.user.email,
                'full_name': voter.user.get_full_name(),
                'verification_status': voter.verification_status,
                'total_documents': docs.count(),
                'pending_documents': pending_docs,
                'verified_documents': verified_docs,
                'created_at': voter.created_at
            })
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def approve_voter(self, request):
        """Approve a voter for participation"""
        voter_id = request.data.get('voter_id')
        notes = request.data.get('notes', '')
        
        try:
            voter = VoterProfile.objects.get(id=voter_id)
        except VoterProfile.DoesNotExist:
            return Response(
                {'error': 'Voter not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check eligibility
        is_eligible, reasons = voter.validate_eligibility()
        if not is_eligible:
            return Response(
                {
                    'error': 'Voter does not meet eligibility criteria',
                    'reasons': reasons
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        voter.verification_status = 'verified'
        voter.is_eligible = True
        voter.verified_by = request.user
        voter.verified_at = timezone.now()
        voter.user.status = 'approved'
        voter.user.save()
        voter.save()
        
        # Create log
        VerificationLog.objects.create(
            voter=voter,
            action='voter_approved',
            performed_by=request.user,
            description=f'Voter approved for participation',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={'notes': notes}
        )
        
        logger.info(f"Voter approved: {voter.user.email}")
        
        return Response({
            'message': 'Voter approved successfully',
            'voter_email': voter.user.email,
            'status': 'verified'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def reject_voter(self, request):
        """Reject a voter application"""
        voter_id = request.data.get('voter_id')
        reason = request.data.get('reason', 'Application rejected')
        
        try:
            voter = VoterProfile.objects.get(id=voter_id)
        except VoterProfile.DoesNotExist:
            return Response(
                {'error': 'Voter not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        voter.verification_status = 'rejected'
        voter.is_eligible = False
        voter.ineligibility_reason = reason
        voter.verified_by = request.user
        voter.verified_at = timezone.now()
        voter.user.status = 'rejected'
        voter.user.save()
        voter.save()
        
        # Create log
        VerificationLog.objects.create(
            voter=voter,
            action='voter_rejected',
            performed_by=request.user,
            description=reason,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        logger.warning(f"Voter rejected: {voter.user.email}")
        
        return Response({
            'message': 'Voter application rejected',
            'voter_email': voter.user.email,
            'reason': reason
        }, status=status.HTTP_200_OK)


class EligibilityRuleViewSet(viewsets.ModelViewSet):
    """
    Eligibility rule management (Admin only)
    """
    queryset = EligibilityRule.objects.all()
    serializer_class = EligibilityRuleSerializer
    permission_classes = [IsAdmin]
    
    @action(detail=False, methods=['get'])
    def active_rules(self, request):
        """Get currently active eligibility rules"""
        rules = EligibilityRule.objects.filter(is_active=True)
        serializer = self.get_serializer(rules, many=True)
        return Response(serializer.data)


class VerificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Verification log viewing (Admin only)
    """
    serializer_class = VerificationLogSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Get verification logs"""
        queryset = VerificationLog.objects.all()
        
        # Filter by voter if specified
        voter_id = self.request.query_params.get('voter_id')
        if voter_id:
            queryset = queryset.filter(voter_id=voter_id)
        
        # Filter by action if specified
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset.order_by('-timestamp')
