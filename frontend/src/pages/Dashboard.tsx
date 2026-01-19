import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const votes = [
    { id: 1, election: 'Board Election 2026', position: 'President', candidate: 'Alice Johnson', date: '2026-01-15', status: 'submitted' },
    { id: 2, election: 'Board Election 2026', position: 'Secretary', candidate: 'David Kim', date: '2026-01-15', status: 'submitted' }
  ]

  const elections = [
    { id: 1, name: 'Annual Board Election 2026', status: 'active', endDate: '2026-02-15', positions: 2 },
    { id: 2, name: 'Committee Elections', status: 'upcoming', endDate: '2026-03-01', positions: 3 }
  ]

  const statusBadgeClass = (status: string) => {
    switch (status) {
      case 'verified': return 'badge-success'
      case 'pending': return 'badge-warning'
      case 'eligible': return 'badge-success'
      case 'ineligible': return 'badge-danger'
      case 'active': return 'badge-success'
      case 'upcoming': return 'badge-info'
      case 'submitted': return 'badge-success'
      default: return 'badge-neutral'
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Mobile Menu Toggle */}
      <button 
        className="mobile-menu-toggle"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle menu"
      >
        ☰
      </button>

      {/* Sidebar */}
      <aside className={`dashboard-sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
        {/* Close button for mobile */}
        <button 
          className="mobile-menu-close"
          onClick={() => setMobileMenuOpen(false)}
          aria-label="Close menu"
        >
          ✕
        </button>

        {/* Profile Section */}
        <div className="sidebar-profile">
          <div className="sidebar-avatar">{user?.firstName[0]}{user?.lastName[0]}</div>
          <h3 className="sidebar-name">{user?.firstName} {user?.lastName}</h3>
          <p className="sidebar-email">{user?.email}</p>
          <span className={`badge ${statusBadgeClass(user?.status || 'pending')}`}>
            {user?.status.charAt(0).toUpperCase() + user?.status.slice(1)}
          </span>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <Link to="/dashboard" className="nav-item active">
            <span className="nav-icon">📊</span>
            <span>Dashboard</span>
          </Link>
          <Link to="/voting" className="nav-item">
            <span className="nav-icon">🗳️</span>
            <span>Vote</span>
          </Link>
          <Link to="/dashboard" className="nav-item">
            <span className="nav-icon">📜</span>
            <span>My Elections</span>
          </Link>
          <Link to="/dashboard" className="nav-item">
            <span className="nav-icon">📈</span>
            <span>History</span>
          </Link>
          <Link to="/dashboard" className="nav-item">
            <span className="nav-icon">⚙️</span>
            <span>Settings</span>
          </Link>
        </nav>

        {/* Stats in Sidebar */}
        <div className="sidebar-stats">
          <div className="sidebar-stat">
            <div className="stat-value">{votes.length}</div>
            <div className="stat-label">Votes Cast</div>
          </div>
          <div className="sidebar-stat">
            <div className="stat-value">{elections.length}</div>
            <div className="stat-label">Elections</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="dashboard-main">
        <div className="dashboard-content">
          {/* Greeting Section */}
          <div className="dashboard-greeting">
            <h1 className="greeting-title">Welcome back, {user?.firstName}!</h1>
            <p className="greeting-subtitle">Your secure voting dashboard</p>
          </div>

          {/* Quick Stats */}
          <div className="stats-row">
            <div className="stat-box">
              <div className="stat-icon">🗳️</div>
              <div className="stat-info">
                <div className="stat-number">{elections.length}</div>
                <div className="stat-text">Active Elections</div>
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-icon">✓</div>
              <div className="stat-info">
                <div className="stat-number">{votes.length}</div>
                <div className="stat-text">Votes Cast</div>
              </div>
            </div>
            <div className="stat-box">
              <div className="stat-icon">📊</div>
              <div className="stat-info">
                <div className="stat-number">100%</div>
                <div className="stat-text">Participation</div>
              </div>
            </div>
          </div>
          {/* Elections Section */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Active Elections</h3>
            </div>
            <div className="card-body">
              <table className="compact-table">
                <thead>
                  <tr>
                    <th>Election</th>
                    <th>Positions</th>
                    <th>Status</th>
                    <th>End Date</th>
                  </tr>
                </thead>
                <tbody>
                  {elections.map((e) => (
                    <tr key={e.id}>
                      <td><strong>{e.name}</strong></td>
                      <td>{e.positions}</td>
                      <td><span className={`badge ${statusBadgeClass(e.status)}`}>{e.status}</span></td>
                      <td>{e.endDate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Voting History Section */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Your Voting History</h3>
            </div>
            <div className="card-body">
              {votes.length > 0 ? (
                <table className="compact-table">
                  <thead>
                    <tr>
                      <th>Election</th>
                      <th>Position</th>
                      <th>Candidate Selected</th>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {votes.map((v) => (
                      <tr key={v.id}>
                        <td>{v.election}</td>
                        <td>{v.position}</td>
                        <td><strong>{v.candidate}</strong></td>
                        <td>{v.date}</td>
                        <td><span className={`badge ${statusBadgeClass(v.status)}`}>✓ {v.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted">No votes cast yet. Visit the voting page to participate in elections.</p>
              )}
            </div>
          </div>

          {/* Actions Section */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Quick Actions</h3>
            </div>
            <div className="card-body">
              <div className="action-buttons">
                <Link to="/voting" className="btn btn-primary btn-sm">Vote Now</Link>
                <Link to="/" className="btn btn-outline btn-sm">View More Elections</Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
