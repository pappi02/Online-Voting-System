"""
Export functionality for election results
Supports CSV, Excel, and PDF formats
"""

import csv
import io
import json
from datetime import datetime
from typing import BinaryIO, List, Dict, Any

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .analytics import VoteAnalytics
from elections.models import Election


class CSVExporter:
    """Export election results to CSV format"""
    
    @staticmethod
    def export_results(election: Election) -> HttpResponse:
        """Export election results as CSV"""
        analytics = VoteAnalytics(election)
        positions = analytics.get_position_statistics()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="election_results_{election.id}.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Election Results Export'])
        writer.writerow(['Election:', election.title])
        writer.writerow(['Type:', election.get_election_type_display()])
        writer.writerow(['Date:', election.scheduled_start.strftime('%Y-%m-%d')])
        writer.writerow([])
        
        # Summary
        summary = analytics.get_summary_statistics()
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Total Votes:', summary['total_votes']])
        writer.writerow(['Eligible Voters:', summary['eligible_voters']])
        writer.writerow(['Turnout %:', f"{summary['turnout_percentage']}%"])
        writer.writerow(['Verification Rate:', f"{summary['verification_rate']}%"])
        writer.writerow([])
        
        # Results by position
        for position in positions:
            writer.writerow([])
            writer.writerow([f"Position: {position['position_title']}"])
            writer.writerow(['Candidates to Elect:', position['candidates_per_voter']])
            writer.writerow(['Total Votes:', position['total_votes']])
            writer.writerow([])
            
            # Candidate results
            writer.writerow(['Rank', 'Candidate', 'Party', 'Votes', 'Percentage'])
            for idx, candidate in enumerate(position['candidates'], 1):
                writer.writerow([
                    idx,
                    candidate['name'],
                    candidate['party'],
                    candidate['votes'],
                    f"{candidate['percentage']}%"
                ])
            
            # Winner
            if position['winner']:
                writer.writerow([])
                writer.writerow(['Winner:', position['winner']['name']])
        
        # Footer
        writer.writerow([])
        writer.writerow(['Generated:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        
        return response
    
    @staticmethod
    def export_turnout(election: Election) -> HttpResponse:
        """Export turnout analysis as CSV"""
        analytics = VoteAnalytics(election)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="turnout_{election.id}.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['Voter Turnout Analysis'])
        writer.writerow(['Election:', election.title])
        writer.writerow([])
        
        # Hourly distribution
        writer.writerow(['Votes by Hour'])
        writer.writerow(['Hour', 'Votes'])
        for entry in analytics.get_votes_by_hour():
            writer.writerow([f"{entry['hour']}:00", entry['votes']])
        
        writer.writerow([])
        
        # Daily distribution
        writer.writerow(['Votes by Day'])
        writer.writerow(['Date', 'Votes'])
        for entry in analytics.get_votes_by_day():
            writer.writerow([entry['date'], entry['votes']])
        
        return response


class ExcelExporter:
    """Export election results to Excel format"""
    
    @staticmethod
    def export_results(election: Election) -> HttpResponse:
        """Export election results as Excel"""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
        except ImportError:
            raise ImportError("openpyxl is required for Excel export. Install it with: pip install openpyxl")
        
        analytics = VoteAnalytics(election)
        positions = analytics.get_position_statistics()
        summary = analytics.get_summary_statistics()
        
        # Create workbook
        wb = openpyxl.Workbook()
        
        # Summary sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Header styling
        header_font = Font(bold=True, size=14)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        # Title
        ws_summary['A1'] = 'Election Results'
        ws_summary['A1'].font = Font(bold=True, size=16)
        ws_summary['A2'] = election.title
        ws_summary['A3'] = f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Summary statistics
        row = 5
        ws_summary[f'A{row}'] = 'Summary Statistics'
        ws_summary[f'A{row}'].font = header_font
        row += 1
        
        stats = [
            ('Total Votes', summary['total_votes']),
            ('Eligible Voters', summary['eligible_voters']),
            ('Turnout %', f"{summary['turnout_percentage']}%"),
            ('Verified Votes', summary['verified_votes']),
            ('Verification Rate', f"{summary['verification_rate']}%"),
            ('Positions', summary['positions_count']),
            ('Candidates', summary['candidates_count'])
        ]
        
        for label, value in stats:
            ws_summary[f'A{row}'] = label
            ws_summary[f'B{row}'] = value
            row += 1
        
        # Results sheets (one per position)
        for position in positions:
            ws = wb.create_sheet(title=position['position_title'][:31])  # Excel sheet name limit
            
            # Position info
            ws['A1'] = position['position_title']
            ws['A1'].font = Font(bold=True, size=14)
            ws['A2'] = f"Candidates to Elect: {position['candidates_per_voter']}"
            ws['A3'] = f"Total Votes: {position['total_votes']}"
            
            # Candidate results table
            row = 5
            headers = ['Rank', 'Candidate', 'Party', 'Votes', 'Percentage']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = header_fill
                cell.font = Font(bold=True, color="FFFFFF")
            
            row += 1
            for idx, candidate in enumerate(position['candidates'], 1):
                ws.cell(row=row, column=1, value=idx)
                ws.cell(row=row, column=2, value=candidate['name'])
                ws.cell(row=row, column=3, value=candidate['party'])
                ws.cell(row=row, column=4, value=candidate['votes'])
                ws.cell(row=row, column=5, value=f"{candidate['percentage']}%")
                row += 1
            
            # Winner highlight
            if position['winner']:
                row += 1
                ws[f'A{row}'] = 'Winner:'
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'] = position['winner']['name']
                ws[f'B{row}'].fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
        
        # Save to response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="election_results_{election.id}.xlsx"'
        wb.save(response)
        
        return response


class PDFExporter:
    """Export election results to PDF format"""
    
    @staticmethod
    def export_results(election: Election) -> HttpResponse:
        """Export election results as PDF"""
        analytics = VoteAnalytics(election)
        positions = analytics.get_position_statistics()
        summary = analytics.get_summary_statistics()
        
        # Create PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="election_results_{election.id}.pdf"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#366092'),
            spaceAfter=12
        )
        
        # Title
        story.append(Paragraph('Election Results Report', title_style))
        story.append(Paragraph(election.title, styles['Heading2']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Election info
        info_data = [
            ['Election Type:', election.get_election_type_display()],
            ['Status:', election.get_status_display()],
            ['Start Date:', election.scheduled_start.strftime('%Y-%m-%d %H:%M')],
            ['End Date:', election.scheduled_end.strftime('%Y-%m-%d %H:%M')],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#366092')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Summary statistics
        story.append(Paragraph('Summary Statistics', heading_style))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Votes Cast', str(summary['total_votes'])],
            ['Eligible Voters', str(summary['eligible_voters'])],
            ['Voter Turnout', f"{summary['turnout_percentage']}%"],
            ['Verified Votes', str(summary['verified_votes'])],
            ['Verification Rate', f"{summary['verification_rate']}%"],
            ['Number of Positions', str(summary['positions_count'])],
            ['Number of Candidates', str(summary['candidates_count'])],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(summary_table)
        story.append(PageBreak())
        
        # Position results
        for position in positions:
            story.append(Paragraph(f"Position: {position['position_title']}", heading_style))
            story.append(Paragraph(
                f"Candidates to Elect: {position['candidates_per_voter']} | "
                f"Total Votes: {position['total_votes']}",
                styles['Normal']
            ))
            story.append(Spacer(1, 0.2 * inch))
            
            # Candidate results
            results_data = [['Rank', 'Candidate', 'Party', 'Votes', 'Percentage']]
            
            for idx, candidate in enumerate(position['candidates'], 1):
                results_data.append([
                    str(idx),
                    candidate['name'],
                    candidate['party'],
                    str(candidate['votes']),
                    f"{candidate['percentage']}%"
                ])
            
            results_table = Table(results_data, colWidths=[0.7*inch, 2.2*inch, 1.5*inch, 1*inch, 1.1*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            # Highlight winner (first row)
            if len(results_data) > 1:
                results_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#90EE90')),
                ]))
            
            story.append(results_table)
            
            # Winner announcement
            if position['winner']:
                story.append(Spacer(1, 0.1 * inch))
                winner_text = f"Winner: {position['winner']['name']} ({position['winner']['party']})"
                story.append(Paragraph(winner_text, styles['Heading3']))
            
            story.append(Spacer(1, 0.4 * inch))
        
        # Footer
        story.append(Spacer(1, 0.5 * inch))
        footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d at %H:%M:%S')}"
        story.append(Paragraph(footer_text, styles['Italic']))
        
        # Build PDF
        doc.build(story)
        
        return response


class JSONExporter:
    """Export election data as JSON"""
    
    @staticmethod
    def export_complete_report(election: Election) -> HttpResponse:
        """Export complete analytics report as JSON"""
        analytics = VoteAnalytics(election)
        report = analytics.get_complete_report()
        
        # Convert datetime objects to strings
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="election_report_{election.id}.json"'
        response.write(json.dumps(report, indent=2, default=json_serial))
        
        return response


__all__ = [
    'CSVExporter',
    'ExcelExporter',
    'PDFExporter',
    'JSONExporter'
]
