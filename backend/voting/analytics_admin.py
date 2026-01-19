"""
Admin interface extensions for analytics
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.shortcuts import redirect

from elections.models import Election
from .analytics import VoteAnalytics


class AnalyticsAdminMixin:
    """
    Mixin to add analytics links to admin interfaces
    """
    
    def analytics_link(self, obj):
        """Generate analytics link for election"""
        if hasattr(obj, 'election'):
            election = obj.election
        else:
            election = obj
        
        if not isinstance(election, Election):
            return "-"
        
        url = reverse('admin:analytics_dashboard', args=[election.id])
        return format_html(
            '<a href="{}" class="button">View Analytics</a>',
            url
        )
    analytics_link.short_description = 'Analytics'
    
    def quick_stats(self, obj):
        """Show quick stats for election"""
        if hasattr(obj, 'election'):
            election = obj.election
        else:
            election = obj
        
        if not isinstance(election, Election):
            return "-"
        
        if election.status not in ['ongoing', 'completed', 'results_published']:
            return "-"
        
        analytics = VoteAnalytics(election)
        total_votes = analytics.get_total_votes()
        turnout = analytics.get_turnout_percentage()
        
        return format_html(
            '<strong>{}</strong> votes | <strong>{:.1f}%</strong> turnout',
            total_votes, turnout
        )
    quick_stats.short_description = 'Quick Stats'


def analytics_dashboard_view(request, election_id):
    """
    Analytics dashboard view in admin
    """
    from django.template.response import TemplateResponse
    from django.contrib.admin.views.decorators import staff_member_required
    from django.shortcuts import get_object_or_404
    
    @staff_member_required
    def view(request):
        election = get_object_or_404(Election, id=election_id)
        analytics = VoteAnalytics(election)
        
        # Get comprehensive data
        summary = analytics.get_summary_statistics()
        positions = analytics.get_position_statistics()
        hourly = analytics.get_votes_by_hour()
        audit = analytics.get_audit_statistics()
        
        context = {
            'election': election,
            'summary': summary,
            'positions': positions,
            'hourly_distribution': hourly,
            'audit_stats': audit,
            'title': f'Analytics: {election.title}',
            'site_header': 'iVote Systems Administration',
            'has_permission': True,
        }
        
        return TemplateResponse(
            request,
            'admin/analytics_dashboard.html',
            context
        )
    
    return view(request)


def register_analytics_urls(admin_site):
    """
    Register analytics URLs with admin site
    """
    from django.urls import path
    
    # Add custom URL pattern
    admin_site._registry_urls = getattr(admin_site, '_registry_urls', [])
    admin_site._registry_urls.append(
        path(
            'analytics/<uuid:election_id>/',
            analytics_dashboard_view,
            name='analytics_dashboard'
        )
    )


# Analytics action for election admin
@admin.action(description='View Analytics Dashboard')
def view_analytics_action(modeladmin, request, queryset):
    """Admin action to view analytics for selected elections"""
    if queryset.count() == 1:
        election = queryset.first()
        return redirect('admin:analytics_dashboard', election_id=election.id)
    else:
        modeladmin.message_user(
            request,
            "Please select only one election to view analytics."
        )


@admin.action(description='Export Results (CSV)')
def export_csv_action(modeladmin, request, queryset):
    """Admin action to export results as CSV"""
    from .exports import CSVExporter
    
    if queryset.count() == 1:
        election = queryset.first()
        return CSVExporter.export_results(election)
    else:
        modeladmin.message_user(
            request,
            "Please select only one election to export."
        )


@admin.action(description='Export Results (Excel)')
def export_excel_action(modeladmin, request, queryset):
    """Admin action to export results as Excel"""
    from .exports import ExcelExporter
    
    if queryset.count() == 1:
        election = queryset.first()
        return ExcelExporter.export_results(election)
    else:
        modeladmin.message_user(
            request,
            "Please select only one election to export."
        )


@admin.action(description='Export Results (PDF)')
def export_pdf_action(modeladmin, request, queryset):
    """Admin action to export results as PDF"""
    from .exports import PDFExporter
    
    if queryset.count() == 1:
        election = queryset.first()
        return PDFExporter.export_results(election)
    else:
        modeladmin.message_user(
            request,
            "Please select only one election to export."
        )


__all__ = [
    'AnalyticsAdminMixin',
    'analytics_dashboard_view',
    'register_analytics_urls',
    'view_analytics_action',
    'export_csv_action',
    'export_excel_action',
    'export_pdf_action',
]
