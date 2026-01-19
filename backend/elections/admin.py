from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
	Election, Position, Candidate, ElectionVoter,
	ElectionSchedule, ElectionInvite
)

# Import analytics actions
from voting.analytics_admin import (
	view_analytics_action,
	export_csv_action,
	export_excel_action,
	export_pdf_action
)


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
	"""Admin for Elections"""
    
	list_display = [
		'title', 'election_type', 'status_badge',
		'scheduled_start', 'position_count', 'candidate_count',
		'voter_count', 'participation_rate_display'
	]
	list_filter = ['status', 'election_type', 'scheduled_start', 'created_at']
	search_fields = ['title', 'description', 'created_by__email']
	readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'modified_by']
    
	fieldsets = (
		('Basic Information', {
			'fields': ('id', 'title', 'description', 'election_type', 'status')
		}),
		('Schedule', {
			'fields': ('scheduled_start', 'scheduled_end')
		}),
		('Voter Eligibility', {
			'fields': ('allow_all_eligible', 'eligible_voters')
		}),
		('Election Settings', {
			'fields': ('allow_multiple_candidates', 'results_visible_before_close', 'require_voter_authentication')
		}),
		('Audit Information', {
			'fields': ('created_by', 'created_at', 'modified_by', 'updated_at'),
			'classes': ('collapse',)
		})
	)
    
	filter_horizontal = ['eligible_voters']
	date_hierarchy = 'scheduled_start'
	actions = [
		view_analytics_action,
		export_csv_action,
		export_excel_action,
		export_pdf_action
	]
    
	def status_badge(self, obj):
		"""Display status with color badge"""
		colors = {
			'draft': '#999999',
			'scheduled': '#0066cc',
			'active': '#00cc00',
			'paused': '#ffcc00',
			'closed': '#cc0000',
			'cancelled': '#666666'
		}
		color = colors.get(obj.status, '#999999')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_badge.short_description = 'Status'
    
	def position_count(self, obj):
		"""Display position count"""
		return obj.positions.count()
	position_count.short_description = 'Positions'
    
	def candidate_count(self, obj):
		"""Display candidate count"""
		return Candidate.objects.filter(
			position__election=obj,
			status='approved'
		).count()
	candidate_count.short_description = 'Candidates'
    
	def voter_count(self, obj):
		"""Display voter count"""
		return obj.get_voter_count()
	voter_count.short_description = 'Eligible Voters'
    
	def participation_rate_display(self, obj):
		"""Display participation rate"""
		rate = obj.get_participation_rate()
		return f"{rate}%"
	participation_rate_display.short_description = 'Participation Rate'


class PositionInline(admin.TabularInline):
	"""Inline admin for positions"""
	model = Position
	extra = 1
	fields = ['title', 'seats_available', 'candidates_per_voter', 'display_order']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
	"""Admin for Positions"""
    
	list_display = ['title', 'election', 'seats_available', 'candidates_per_voter', 'candidate_count', 'display_order']
	list_filter = ['election', 'created_at']
	search_fields = ['title', 'election__title']
	readonly_fields = ['id', 'created_at', 'updated_at']
    
	fieldsets = (
		('Basic Information', {
			'fields': ('id', 'election', 'title', 'description')
		}),
		('Voting Constraints', {
			'fields': ('seats_available', 'candidates_per_voter')
		}),
		('Ordering', {
			'fields': ('display_order',)
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
    
	def candidate_count(self, obj):
		"""Display candidate count"""
		return obj.get_candidate_count()
	candidate_count.short_description = 'Candidates'
    
	def get_queryset(self, request):
		return super().get_queryset(request).select_related('election')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
	"""Admin for Candidates"""
    
	list_display = [
		'full_name', 'position', 'user_link',
		'status_badge', 'vote_count', 'approved_at'
	]
	list_filter = ['status', 'position__election', 'created_at', 'approved_at']
	search_fields = ['full_name', 'user__email', 'party_affiliation']
	readonly_fields = ['id', 'created_at', 'updated_at', 'vote_count_display']
    
	fieldsets = (
		('Basic Information', {
			'fields': ('id', 'position', 'user', 'full_name')
		}),
		('Candidate Profile', {
			'fields': ('biography', 'party_affiliation', 'website_url', 'email', 'phone', 'resume')
		}),
		('Status & Approval', {
			'fields': ('status', 'approval_notes', 'approved_by', 'approved_at')
		}),
		('Statistics', {
			'fields': ('vote_count_display',),
			'classes': ('collapse',)
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
    
	actions = ['approve_candidates', 'reject_candidates', 'reset_to_pending']
    
	def user_link(self, obj):
		"""Display user with link"""
		if obj.user:
			url = reverse('admin:accounts_user_change', args=[obj.user.id])
			return format_html('<a href="{}">{}</a>', url, obj.user.email)
		return '-'
	user_link.short_description = 'User Account'
    
	def status_badge(self, obj):
		"""Display status with color badge"""
		colors = {
			'pending': '#ffcc00',
			'approved': '#00cc00',
			'rejected': '#cc0000',
			'withdrawn': '#999999'
		}
		color = colors.get(obj.status, '#999999')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_badge.short_description = 'Status'
    
	def vote_count(self, obj):
		"""Display vote count"""
		return obj.get_vote_count()
	vote_count.short_description = 'Votes'
    
	def vote_count_display(self, obj):
		"""Readonly field for vote count"""
		return obj.get_vote_count()
	vote_count_display.short_description = 'Total Votes Received'
    
	def approve_candidates(self, request, queryset):
		"""Admin action to approve candidates"""
		updated = 0
		for candidate in queryset.filter(status='pending'):
			candidate.approve(request.user, 'Approved via admin action')
			updated += 1
		self.message_user(request, f'{updated} candidates approved')
	approve_candidates.short_description = 'Approve selected candidates'
    
	def reject_candidates(self, request, queryset):
		"""Admin action to reject candidates"""
		updated = 0
		for candidate in queryset.filter(status='pending'):
			candidate.reject(request.user, 'Rejected via admin action')
			updated += 1
		self.message_user(request, f'{updated} candidates rejected')
	reject_candidates.short_description = 'Reject selected candidates'
    
	def reset_to_pending(self, request, queryset):
		"""Admin action to reset status to pending"""
		updated = queryset.exclude(status='approved').update(
			status='pending',
			approved_by=None,
			approved_at=None
		)
		self.message_user(request, f'{updated} candidates reset to pending')
	reset_to_pending.short_description = 'Reset to pending review'
    
	def get_queryset(self, request):
		return super().get_queryset(request).select_related('position', 'user', 'approved_by')


@admin.register(ElectionVoter)
class ElectionVoterAdmin(admin.ModelAdmin):
	"""Admin for Election Voters"""
    
	list_display = ['voter_email', 'election', 'status_badge', 'voted_at', 'created_at']
	list_filter = ['status', 'election', 'voted_at', 'created_at']
	search_fields = ['voter__user__email', 'election__title']
	readonly_fields = ['id', 'created_at', 'updated_at', 'ip_address']
    
	fieldsets = (
		('Election & Voter', {
			'fields': ('id', 'election', 'voter')
		}),
		('Voting Information', {
			'fields': ('status', 'voted_at', 'ip_address', 'user_agent')
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
    
	def voter_email(self, obj):
		"""Display voter email"""
		return obj.voter.user.email
	voter_email.short_description = 'Voter Email'
    
	def status_badge(self, obj):
		"""Display status with color badge"""
		colors = {
			'eligible': '#0066cc',
			'voted': '#00cc00',
			'abstained': '#ffcc00',
			'ineligible': '#cc0000'
		}
		color = colors.get(obj.status, '#999999')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_badge.short_description = 'Status'
    
	def get_queryset(self, request):
		return super().get_queryset(request).select_related('election', 'voter', 'voter__user')


@admin.register(ElectionSchedule)
class ElectionScheduleAdmin(admin.ModelAdmin):
	"""Admin for Election Schedules"""
    
	list_display = ['election', 'current_state', 'pending_action', 'pending_action_time']
	list_filter = ['current_state', 'pending_action']
	search_fields = ['election__title']
	readonly_fields = ['id', 'created_at', 'updated_at']
    
	fieldsets = (
		('Election', {
			'fields': ('id', 'election')
		}),
		('State Management', {
			'fields': ('current_state',)
		}),
		('Pending Action', {
			'fields': ('pending_action', 'pending_action_time')
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
    
	def get_queryset(self, request):
		return super().get_queryset(request).select_related('election')


@admin.register(ElectionInvite)
class ElectionInviteAdmin(admin.ModelAdmin):
	"""Admin for Election Invites"""
    
	list_display = [
		'recipient_email', 'election', 'position',
		'status_badge', 'sent_at', 'expires_at'
	]
	list_filter = ['status', 'election', 'position', 'sent_at']
	search_fields = ['recipient_email', 'election__title', 'position__title']
	readonly_fields = ['id', 'sent_at', 'accepted_at']
    
	fieldsets = (
		('Invitation Details', {
			'fields': ('id', 'election', 'position')
		}),
		('Recipient', {
			'fields': ('recipient_email', 'recipient_name', 'accepted_by')
		}),
		('Status & Dates', {
			'fields': ('status', 'sent_at', 'accepted_at', 'expires_at')
		})
	)
    
	actions = ['resend_invitations']
    
	def status_badge(self, obj):
		"""Display status with color badge"""
		colors = {
			'sent': '#0066cc',
			'accepted': '#00cc00',
			'declined': '#cc0000',
			'expired': '#999999'
		}
		color = colors.get(obj.status, '#999999')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_badge.short_description = 'Status'
    
	def resend_invitations(self, request, queryset):
		"""Admin action to resend invitations"""
		# This would integrate with your notification service
		count = queryset.filter(status='sent').count()
		self.message_user(request, f'{count} invitations ready to resend')
	resend_invitations.short_description = 'Resend invitations'
    
	def get_queryset(self, request):
		return super().get_queryset(request).select_related('election', 'position', 'accepted_by')
