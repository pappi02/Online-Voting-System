# Phase 5 Quick Reference

## Analytics API Endpoints

### Get Complete Report
```bash
GET /api/voting/analytics/{election_id}/complete_report/
```

### Get Summary
```bash
GET /api/voting/analytics/{election_id}/summary/
```

### Get Position Results
```bash
GET /api/voting/analytics/{election_id}/position_results/
```

### Real-Time Stats
```bash
GET /api/voting/analytics/{election_id}/real_time_stats/
```

### Dashboard Stats
```bash
GET /api/voting/analytics/dashboard/
```

## Export Endpoints

### CSV Export
```bash
GET /api/voting/exports/{election_id}/csv/
```

### Excel Export
```bash
GET /api/voting/exports/{election_id}/excel/
```

### PDF Export
```bash
GET /api/voting/exports/{election_id}/pdf/
```

### JSON Export
```bash
GET /api/voting/exports/{election_id}/json/
```

## Python Usage

### Basic Analytics
```python
from voting.analytics import VoteAnalytics

analytics = VoteAnalytics(election)
total_votes = analytics.get_total_votes()
turnout = analytics.get_turnout_percentage()
results = analytics.get_position_statistics()
```

### Turnout Analysis
```python
from voting.analytics import TurnoutAnalytics

trend = TurnoutAnalytics.get_turnout_trend(election)
peaks = TurnoutAnalytics.get_peak_voting_times(election)
```

### Export Results
```python
from voting.exports import PDFExporter, CSVExporter

# PDF Export
pdf = PDFExporter.export_results(election)

# CSV Export
csv = CSVExporter.export_results(election)
```

### Compare Elections
```python
from voting.analytics import ComparisonAnalytics

comparisons = ComparisonAnalytics.compare_elections([
    'uuid1', 'uuid2', 'uuid3'
])
```

## Admin Actions

1. Select election in admin
2. Choose action:
   - View Analytics Dashboard
   - Export Results (CSV)
   - Export Results (Excel)
   - Export Results (PDF)

## Key Files

- `voting/analytics.py` - Analytics engine
- `voting/exports.py` - Export functionality
- `voting/analytics_views.py` - REST API
- `voting/analytics_serializers.py` - Serializers
- `voting/analytics_admin.py` - Admin interface

## Testing

```bash
pytest test_phase5.py -v
```

## Dependencies

```bash
pip install openpyxl reportlab Pillow
```
