"""
Voting admin interface
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Vote, VoteAudit, VoteVerification


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """
    Admin interface for Vote model
    """
    list_display = [
        'verification_code', 'election', 'cast_at',
        'verified_status', 'voter_hash_short'
    ]
    list_filter = [
        'election', 'cast_at', 'verified_at'
    ]
    search_fields = [
        'verification_code', 'voter_hash', 'election__title'
    ]
    readonly_fields = [
        'id', 'election', 'encrypted_vote', 'encryption_iv',
        'voter_hash', 'cast_at', 'verification_code',
        'verified_at', 'ip_address', 'user_agent',
        'decrypted_data_display'
    ]
    
    fieldsets = (
        ('Vote Information', {
            'fields': ('id', 'verification_code', 'election')
        }),
        ('Encrypted Data', {
            'fields': ('encrypted_vote', 'encryption_iv', 'voter_hash'),
            'classes': ('collapse',)
        }),
        ('Decrypted Vote', {
            'fields': ('decrypted_data_display',),
            'description': 'Only visible to superusers'
        }),
        ('Metadata', {
            'fields': ('cast_at', 'verified_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Votes cannot be added through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Votes cannot be modified"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete votes"""
        return request.user.is_superuser
    
    def verified_status(self, obj):
        """Display verification status"""
        if obj.verified_at:
            return format_html(
                '<span style="color: green;">✓ Verified</span> ({})',
                obj.verified_at.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<span style="color: gray;">Not verified</span>')
    verified_status.short_description = 'Verification Status'
    
    def voter_hash_short(self, obj):
        """Display shortened voter hash"""
        return f"{obj.voter_hash[:8]}...{obj.voter_hash[-8:]}"
    voter_hash_short.short_description = 'Voter Hash'
    
    def decrypted_data_display(self, obj):
        """Display decrypted vote data (superuser only)"""
        if not self.has_view_permission:
            return format_html('<span style="color: red;">Access Denied</span>')
        
        try:
            vote_data = obj.decrypt_vote_data()
            
            # Format for display
            html = '<table style="border-collapse: collapse;">'
            
            for position_id, candidate_ids in vote_data.items():
                # Get position details
                from elections.models import Position, Candidate
                try:
                    position = Position.objects.get(id=position_id)
                    position_name = position.title
                except Position.DoesNotExist:
                    position_name = f"Position {position_id}"
                
                html += f'<tr><td style="padding: 5px;"><strong>{position_name}:</strong></td><td style="padding: 5px;">'
                
                # Get candidate names
                candidate_names = []
                for candidate_id in candidate_ids:
                    try:
                        candidate = Candidate.objects.get(id=candidate_id)
                        candidate_names.append(f"{candidate.name} ({candidate.party})")
                    except Candidate.DoesNotExist:
                        candidate_names.append(f"Unknown ({candidate_id})")
                
                html += ', '.join(candidate_names)
                html += '</td></tr>'
            
            html += '</table>'
            
            # Log decryption access
            VoteAudit.log_action(
                action='vote_viewed',
                election=obj.election,
                vote=obj,
                performed_by=self.model._meta.app_config.name,  # Admin access
                details={'context': 'admin_interface'}
            )
            
            return format_html(html)
        
        except Exception as e:
            return format_html(
                '<span style="color: red;">Error: {}</span>',
                str(e)
            )
    decrypted_data_display.short_description = 'Decrypted Vote Data'


@admin.register(VoteAudit)
class VoteAuditAdmin(admin.ModelAdmin):
    """
    Admin interface for VoteAudit model
    """
    list_display = [
        'timestamp', 'action', 'election', 'performed_by', 'ip_address'
    ]
    list_filter = [
        'action', 'timestamp', 'election'
    ]
    search_fields = [
        'election__title', 'performed_by__email', 'ip_address'
    ]
    readonly_fields = [
        'id', 'action', 'election', 'vote', 'performed_by',
        'details', 'ip_address', 'user_agent', 'timestamp'
    ]
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('id', 'timestamp', 'action')
        }),
        ('Context', {
            'fields': ('election', 'vote', 'performed_by')
        }),
        ('Details', {
            'fields': ('details', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Audit logs cannot be added manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs"""
        return request.user.is_superuser


@admin.register(VoteVerification)
class VoteVerificationAdmin(admin.ModelAdmin):
    """
    Admin interface for VoteVerification model
    """
    list_display = [
        'verification_code', 'verified', 'attempted_at', 'ip_address', 'vote_link'
    ]
    list_filter = [
        'verified', 'attempted_at'
    ]
    search_fields = [
        'verification_code', 'ip_address', 'vote__verification_code'
    ]
    readonly_fields = [
        'id', 'verification_code', 'vote', 'verified',
        'attempted_at', 'ip_address'
    ]
    
    fieldsets = (
        ('Verification Attempt', {
            'fields': ('id', 'verification_code', 'verified', 'attempted_at')
        }),
        ('Associated Vote', {
            'fields': ('vote',)
        }),
        ('Context', {
            'fields': ('ip_address',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Verification attempts cannot be added manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Verification attempts are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete verification attempts"""
        return request.user.is_superuser
    
    def vote_link(self, obj):
        """Display link to associated vote"""
        if obj.vote:
            url = reverse('admin:voting_vote_change', args=[obj.vote.id])
            return format_html('<a href="{}">View Vote</a>', url)
        return format_html('<span style="color: gray;">No vote found</span>')
    vote_link.short_description = 'Associated Vote'
