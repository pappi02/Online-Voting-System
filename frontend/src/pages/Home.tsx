import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-text">
            <h1 className="hero-title">Secure Online Voting Platform</h1>
            <p className="hero-subtitle">Experience transparent, secure, and accessible voting with iVote Systems</p>
            <div className="hero-cta">
              <Link to="/voting" className="btn btn-primary btn-lg">Cast Your Vote</Link>
              <Link to="/login" className="btn btn-secondary btn-lg">Login</Link>
            </div>
          </div>
          <div className="hero-visual">
            <div className="ballot-icon">🗳️</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-header">
          <h2>Why Choose iVote?</h2>
          <p>Industry-leading security and accessibility</p>
        </div>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>End-to-End Encryption</h3>
            <p>Your votes are protected with military-grade encryption, ensuring complete privacy and security</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">✓</div>
            <h3>Verified Authentication</h3>
            <p>Multi-factor authentication and voter verification ensure only eligible voters can participate</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Real-Time Results</h3>
            <p>View live election results with detailed analytics and transparent vote counting</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">♿</div>
            <h3>Accessible Design</h3>
            <p>Fully accessible interface with support for screen readers and keyboard navigation</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🌍</div>
            <h3>Remote Voting</h3>
            <p>Vote from anywhere, anytime with our secure cloud-based platform</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📋</div>
            <h3>Audit Trail</h3>
            <p>Complete transparency with immutable audit logs for every transaction</p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works-section">
        <div className="section-header">
          <h2>How It Works</h2>
          <p>Simple, secure, and transparent voting in 4 steps</p>
        </div>
        <div className="steps-container">
          <div className="step">
            <div className="step-number">1</div>
            <h3>Register & Verify</h3>
            <p>Create your account and verify your eligibility</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>Review Candidates</h3>
            <p>Browse detailed candidate information and positions</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Cast Your Vote</h3>
            <p>Securely select and submit your encrypted vote</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">4</div>
            <h3>Get Verification</h3>
            <p>Receive verification code to confirm your vote</p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">10K+</div>
            <p>Active Users</p>
          </div>
          <div className="stat-card">
            <div className="stat-number">99.9%</div>
            <p>Uptime</p>
          </div>
          <div className="stat-card">
            <div className="stat-number">256-bit</div>
            <p>Encryption</p>
          </div>
          <div className="stat-card">
            <div className="stat-number">24/7</div>
            <p>Support</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>Ready to Vote?</h2>
        <p>Join thousands of voters using iVote for secure, transparent elections</p>
        <div className="cta-buttons">
          <Link to="/voting" className="btn btn-primary btn-lg">Start Voting</Link>
          <Link to="/register" className="btn btn-outline btn-lg">Create Account</Link>
        </div>
      </section>
    </div>
  )
}
