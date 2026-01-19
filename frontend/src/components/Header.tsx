import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Header() {
  const { isAuthenticated, logout, user } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="logo">
          🗳️ iVote Systems
        </Link>
        <ul className="nav-links">
          <li><Link to="/">Home</Link></li>
          {isAuthenticated && <li><Link to="/voting">Voting</Link></li>}
          {isAuthenticated && <li><Link to="/dashboard">Dashboard</Link></li>}
          {!isAuthenticated && <li><Link to="/login">Login</Link></li>}
          {!isAuthenticated && <li><Link to="/register">Register</Link></li>}
          {isAuthenticated && (
            <li className="user-menu">
              <span className="user-email">{user?.email}</span>
              <button onClick={handleLogout} className="btn-logout">Logout</button>
            </li>
          )}
        </ul>
      </div>
    </nav>
  )
}
