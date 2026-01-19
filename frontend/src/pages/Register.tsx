import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import OTPVerificationModal from '../components/OTPVerificationModal'
import Notification from '../components/Notification'

export default function Register() {
  const [formData, setFormData] = useState({
    email: '',
    firstName: '',
    lastName: '',
    password: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState<{ [key: string]: string }>({})
  const [showOTPModal, setShowOTPModal] = useState(false)
  const [otpCode, setOtpCode] = useState('')
  const [notification, setNotification] = useState({ isVisible: false, type: 'info' as 'info' | 'success' | 'error' | 'warning', message: '' })
  const [isLoading, setIsLoading] = useState(false)
  const { completeSignup } = useAuth()
  const navigate = useNavigate()

  const deriveApiBase = () => {
    const envBase = import.meta.env.VITE_API_BASE
    if (envBase) return envBase

    const origin = window.location.origin
    if (origin.includes('app.github.dev')) {
      // Codespaces: swap frontend port suffix to 8000
      return origin.replace('-3000', '-8000') + '/accounts'
    }

    return 'http://localhost:8000/accounts'
  }

  const API_BASE = deriveApiBase()

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {}

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required'
    }
    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required'
    }
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format'
    }
    if (!formData.password) {
      newErrors.password = 'Password is required'
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters'
    }
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    // Clear error for this field when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const requestOTP = async () => {
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE}/auth/register/request-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: formData.firstName,
          last_name: formData.lastName,
          email: formData.email,
          password: formData.password,
          password_confirm: formData.confirmPassword
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data?.email?.[0] || data?.password?.[0] || data?.error || 'Failed to send verification code')
      }

      const data = await response.json()
      const codeFromServer = data?.otp_code || ''
      setOtpCode(codeFromServer)

      setNotification({
        isVisible: true,
        type: 'info',
        message: data?.message || `Verification code sent to ${formData.email}. Please check your email.`
      })

      setShowOTPModal(true)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      await requestOTP()
    } catch (error: any) {
      setNotification({
        isVisible: true,
        type: 'error',
        message: error?.message || 'Failed to send verification code. Please try again.'
      })
      setIsLoading(false)
    }
  }

  const handleOTPSuccess = () => {
    setShowOTPModal(false)
    setNotification({
      isVisible: true,
      type: 'success',
      message: 'Email verified successfully! Redirecting to dashboard...'
    })

    // Redirect after a short delay
    setTimeout(() => {
      navigate('/dashboard')
    }, 1500)
  }

  return (
    <div className="page register-page">
      <div className="content-container">
        <div className="page-header">
          <h1 className="page-title">Create Your Account</h1>
          <p className="page-subtitle">Register to securely participate in elections</p>
        </div>

        <div className="card">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="form-grid" aria-label="Registration form">
              <div className="form-group">
                <label htmlFor="firstName">First Name</label>
                <input
                  type="text"
                  id="firstName"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleChange}
                  disabled={isLoading}
                  className={errors.firstName ? 'input-error' : ''}
                />
                {errors.firstName && <span className="error-message">{errors.firstName}</span>}
              </div>
              <div className="form-group">
                <label htmlFor="lastName">Last Name</label>
                <input
                  type="text"
                  id="lastName"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleChange}
                  disabled={isLoading}
                  className={errors.lastName ? 'input-error' : ''}
                />
                {errors.lastName && <span className="error-message">{errors.lastName}</span>}
              </div>
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={isLoading}
                  className={errors.email ? 'input-error' : ''}
                />
                {errors.email && <span className="error-message">{errors.email}</span>}
              </div>
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  disabled={isLoading}
                  className={errors.password ? 'input-error' : ''}
                />
                {errors.password && <span className="error-message">{errors.password}</span>}
              </div>
              <div className="form-group">
                <label htmlFor="confirmPassword">Confirm Password</label>
                <input
                  type="password"
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  disabled={isLoading}
                  className={errors.confirmPassword ? 'input-error' : ''}
                />
                {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
              </div>
              <div className="form-actions">
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={isLoading}
                >
                  {isLoading ? 'Sending Code...' : 'Register'}
                </button>
              </div>
            </form>
            <div className="auth-redirect">
              <p>Already have an account? <Link to="/login" className="auth-link">Login here</Link></p>
            </div>
          </div>
        </div>
      </div>

      <OTPVerificationModal
        isOpen={showOTPModal}
        email={formData.email}
        firstName={formData.firstName}
        lastName={formData.lastName}
        password={formData.password}
        apiBase={API_BASE}
        onCompleteSignup={() => completeSignup(formData.firstName, formData.lastName, formData.email, formData.password)}
        onResend={requestOTP}
        onSuccess={handleOTPSuccess}
        onClose={() => setShowOTPModal(false)}
      />

      <Notification
        type={notification.type}
        message={notification.message}
        isVisible={notification.isVisible}
        onClose={() => setNotification({ ...notification, isVisible: false })}
      />
    </div>
  )
}
