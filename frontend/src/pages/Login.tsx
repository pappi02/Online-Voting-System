import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    login(email, password)
    navigate('/dashboard')
  }

  return (
    <div className="page login-page">
      <div className="content-container">
        <div className="page-header">
          <h1 className="page-title">Login to iVote</h1>
          <p className="page-subtitle">Access your secure voter account</p>
        </div>

        <div className="card">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="form-grid" aria-label="Login form">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary btn-sm">Login</button>
              </div>
            </form>
            <div className="auth-redirect">
              <p>Don't have an account? <Link to="/register" className="auth-link">Register here</Link></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
