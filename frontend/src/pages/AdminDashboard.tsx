import React from 'react'

export default function AdminDashboard() {
  return (
    <div className="page admin-page">
      <div className="content-container">
        <div className="page-header">
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">Manage elections, candidates, and monitor activity</p>
        </div>

        <div className="card">
          <div className="card-body">
            <p className="text-muted">Overview</p>
            <div className="form-grid">
              <div className="form-group">
                <label>Active Elections</label>
                <div>0</div>
              </div>
              <div className="form-group">
                <label>Pending Approvals</label>
                <div>0</div>
              </div>
              <div className="form-group">
                <label>Recent Activity</label>
                <div>No recent events</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
