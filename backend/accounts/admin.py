"""
Django admin configuration for accounts
"""

from django.contrib import admin
from django.utils.html import format_html
from accounts.models import User, OTPVerification, UserAuditLog, NotificationLog
from accounts.voter_models import (
    VoterProfile, VoterDocument, EligibilityRule, VerificationLog
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Admin configuration for User model
    """
    list_display = ['email', 'full_name', 'role_badge', 'status_badge', 'created_at', 'is_active']
    list_filter = ['role', 'status', 'is_active', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'national_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Identity Verification', {
            'fields': ('national_id', 'id_verified')
        }),
        ('Account Status', {
            'fields': ('role', 'status', 'is_active')
        }),
        ('Multi-Factor Authentication', {
            'fields': ('mfa_enabled', 'mfa_method')
        }),
        ('Institution', {
            'fields': ('institution', 'department')
        }),
        ('Voting Info', {
            'fields': ('has_voted',)
        }),
        ('Security', {
            'fields': ('failed_login_attempts', 'locked_until', 'last_password_change'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_password_change']
    
    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = 'Full Name'
    
    def role_badge(self, obj):
        colors = {
            'admin': '#FF6B6B',
            'election_officer': '#4ECDC4',
            'voter': '#45B7D1',
            'observer': '#FFA07A',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.role, '#999'),
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def status_badge(self, obj):
        colors = {
            'approved': '#51CF66',
            'pending': '#FFD43B',
            'rejected': '#FF6B6B',
            'blocked': '#A6142F',
            'inactive': '#999',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for OTP Verification model
    """
    list_display = ['user', 'method_badge', 'purpose', 'is_used', 'created_at', 'expires_at']
    list_filter = ['method', 'purpose', 'is_used', 'created_at']
    search_fields = ['user__email', 'contact_info']
    ordering = ['-created_at']
    readonly_fields = ['otp_code', 'created_at', 'verified_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('OTP Details', {
            'fields': ('otp_code', 'method', 'purpose', 'contact_info')
        }),
        ('Status', {
            'fields': ('is_used', 'verified_at', 'attempts')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def method_badge(self, obj):
        colors = {'sms': '#45B7D1', 'email': '#4ECDC4'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.method, '#999'),
            obj.get_method_display()
        )
    method_badge.short_description = 'Method'


@admin.register(UserAuditLog)
class UserAuditLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for User Audit Log model
    """
    list_display = ['user', 'action_badge', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'ip_address', 'action']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'details']
    
    fieldsets = (
        ('Audit Info', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('Details', {
            'fields': ('description', 'details')
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def action_badge(self, obj):
        colors = {
            'login': '#45B7D1',
            'logout': '#FF6B6B',
            'password_change': '#FFA07A',
            'mfa_enabled': '#51CF66',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.action, '#999'),
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'


@admin.register(VoterProfile)
class VoterProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for Voter Profile model
    """
    list_display = ['user_email', 'age', 'verification_badge', 'is_eligible', 'documents_count', 'created_at']
    list_filter = ['verification_status', 'is_eligible', 'gender', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'verified_at', 'verified_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('id', 'user')
        }),
        ('Biographical Information', {
            'fields': ('date_of_birth', 'gender', 'marital_status')
        }),
        ('Address Information', {
            'fields': ('street_address', 'city', 'state_province', 'postal_code', 'country')
        }),
        ('Professional Information', {
            'fields': ('occupation', 'employer')
        }),
        ('Accessibility', {
            'fields': ('disability_status', 'disability_description')
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'is_eligible', 'ineligibility_reason', 'verified_by', 'verified_at'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def age(self, obj):
        age = obj.calculate_age()
        return f"{age} years" if age else "N/A"
    age.short_description = 'Age'
    
    def verification_badge(self, obj):
        colors = {
            'pending': '#FFD43B',
            'under_review': '#845EF7',
            'verified': '#51CF66',
            'rejected': '#FF6B6B',
            'suspended': '#868E96',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.verification_status, '#999'),
            obj.get_verification_status_display()
        )
    verification_badge.short_description = 'Verification Status'
    
    def documents_count(self, obj):
        return obj.documents.count()
    documents_count.short_description = 'Documents'


@admin.register(VoterDocument)
class VoterDocumentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Voter Document model
    """
    list_display = ['voter_email', 'document_type_display', 'verification_badge', 'is_expired', 'uploaded_at']
    list_filter = ['document_type', 'verification_status', 'uploaded_at']
    search_fields = ['voter__user__email', 'document_number']
    readonly_fields = ['id', 'file_size', 'uploaded_at', 'verified_at']
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('Voter', {
            'fields': ('id', 'voter')
        }),
        ('Document Information', {
            'fields': ('document_type', 'document_number', 'issuing_country', 'issue_date', 'expiry_date')
        }),
        ('Document File', {
            'fields': ('document_file', 'file_size')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verified_by', 'verification_notes', 'verified_at'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def voter_email(self, obj):
        return obj.voter.user.email
    voter_email.short_description = 'Voter Email'
    
    def document_type_display(self, obj):
        return obj.get_document_type_display()
    document_type_display.short_description = 'Document Type'
    
    def verification_badge(self, obj):
        colors = {
            'pending': '#FFD43B',
            'verified': '#51CF66',
            'rejected': '#FF6B6B',
            'expired': '#868E96',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.verification_status, '#999'),
            obj.get_verification_status_display()
        )
    verification_badge.short_description = 'Status'


@admin.register(EligibilityRule)
class EligibilityRuleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Eligibility Rule model
    """
    list_display = ['rule_name', 'rule_type_display', 'is_active', 'minimum_age', 'updated_at']
    list_filter = ['rule_type', 'is_active', 'created_at']
    search_fields = ['rule_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['rule_type', 'rule_name']
    
    fieldsets = (
        ('Rule Information', {
            'fields': ('id', 'rule_name', 'rule_type', 'description', 'is_active')
        }),
        ('Age Requirements', {
            'fields': ('minimum_age', 'maximum_age'),
            'classes': ('collapse',)
        }),
        ('Custom Rule', {
            'fields': ('rule_code',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def rule_type_display(self, obj):
        return obj.get_rule_type_display()
    rule_type_display.short_description = 'Type'


@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for Verification Log model
    """
    list_display = ['voter_email', 'action_badge', 'performed_by_email', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['voter__user__email', 'performed_by__email']
    readonly_fields = ['id', 'timestamp']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Voter & Action', {
            'fields': ('id', 'voter', 'action', 'performed_by')
        }),
        ('Details', {
            'fields': ('description', 'ip_address', 'user_agent', 'details')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def voter_email(self, obj):
        return obj.voter.user.email
    voter_email.short_description = 'Voter Email'
    
    def performed_by_email(self, obj):
        return obj.performed_by.email if obj.performed_by else 'N/A'
    performed_by_email.short_description = 'Verified By'
    
    def action_badge(self, obj):
        colors = {
            'document_verified': '#51CF66',
            'document_rejected': '#FF6B6B',
            'voter_approved': '#51CF66',
            'voter_rejected': '#FF6B6B',
            'eligibility_checked': '#845EF7',
            'profile_updated': '#4ECDC4',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.action, '#999'),
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for Notification Log model
    """
    list_display = ['user_email', 'notification_type_display', 'status_badge', 'sent_at', 'created_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['user__email', 'recipient_email', 'subject']
    readonly_fields = ['id', 'created_at', 'sent_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Recipient', {
            'fields': ('id', 'user', 'recipient_email')
        }),
        ('Notification', {
            'fields': ('notification_type', 'subject')
        }),
        ('Status', {
            'fields': ('status', 'error_message'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def notification_type_display(self, obj):
        return obj.get_notification_type_display()
    notification_type_display.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'sent': '#27ae60',
            'failed': '#e74c3c',
            'pending': '#f39c12',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

