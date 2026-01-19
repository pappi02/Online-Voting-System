import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'

interface OTPVerificationModalProps {
  isOpen: boolean
  email: string
  onSuccess: () => void
  onClose: () => void
  firstName: string
  lastName: string
  password: string
  apiBase: string
  onResend: () => Promise<void> | void
  onCompleteSignup: () => void
}

export default function OTPVerificationModal({
  isOpen,
  email,
  onSuccess,
  onClose,
  firstName,
  lastName,
  password,
  apiBase,
  onResend,
  onCompleteSignup
}: OTPVerificationModalProps) {
  const { login } = useAuth()
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [timeLeft, setTimeLeft] = useState(300) // 5 minutes in seconds
  const [isSubmitting, setIsSubmitting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [resendLoading, setResendLoading] = useState(false)

  useEffect(() => {
    if (!isOpen) return

    // Focus input when modal opens
    inputRef.current?.focus()

    // Timer countdown
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          setError('OTP expired. Please request a new one.')
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isOpen])

  const handleOTPChange = (value: string) => {
    // Only allow numbers and max 6 digits
    const numericValue = value.replace(/\D/g, '').slice(0, 6)
    setOtp(numericValue)
    setError('')

    // Auto-submit when 6 digits are entered
    if (numericValue.length === 6) {
      handleSubmit(numericValue)
    }
  }

  const handleSubmit = async (codeToVerify: string = otp) => {
    if (codeToVerify.length !== 6) {
      setError('Please enter a 6-digit code')
      return
    }

    setIsSubmitting(true)

    try {
      const response = await fetch(`${apiBase}/auth/register/verify-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp_code: codeToVerify })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data?.error || data?.otp_code?.[0] || 'Invalid or expired OTP. Please try again.')
      }

      setError('')
      onCompleteSignup()
      login(email, password)
      onSuccess()
    } catch (err: any) {
      setError(err?.message || 'Invalid or expired OTP. Please try again.')
      setOtp('')
      inputRef.current?.focus()
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResend = async () => {
    setResendLoading(true)
    setError('')
    setOtp('')
    try {
      await onResend()
      setTimeLeft(300)
    } catch (err: any) {
      setError(err?.message || 'Failed to resend code. Please try again.')
    } finally {
      setResendLoading(false)
      inputRef.current?.focus()
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <div className="modal-header">
          <h2 className="modal-title">Verify Your Email</h2>
          <button
            className="modal-close"
            onClick={onClose}
            aria-label="Close modal"
            disabled={isSubmitting}
          >
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="otp-info">
            <div className="otp-icon">📧</div>
            <p className="otp-message">
              We've sent a 6-digit code to<br />
              <strong>{email}</strong>
            </p>
          </div>

          <div className="otp-input-group">
            <label htmlFor="otp-input" className="otp-label">
              Enter Verification Code
            </label>
            <input
              ref={inputRef}
              id="otp-input"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={otp}
              onChange={(e) => handleOTPChange(e.target.value)}
              placeholder="000000"
              className="otp-input"
              disabled={isSubmitting || timeLeft === 0}
              autoFocus
            />
            <div className="otp-divider"></div>
          </div>

          {error && <div className="otp-error">{error}</div>}

          <div className="otp-timer">
            <span className={timeLeft < 60 ? 'timer-warning' : ''}>
              Code expires in: <strong>{formatTime(timeLeft)}</strong>
            </span>
          </div>

          <div className="otp-actions">
            <button
              onClick={() => handleSubmit()}
              disabled={otp.length !== 6 || isSubmitting || timeLeft === 0}
              className="btn btn-primary"
            >
              {isSubmitting ? 'Verifying...' : 'Verify Code'}
            </button>
          </div>

          <div className="otp-footer">
            <p>
              Didn't receive the code?{' '}
              <button
                className="otp-resend"
                disabled={isSubmitting || resendLoading || timeLeft === 0}
                onClick={handleResend}
              >
                {resendLoading ? 'Resending...' : 'Request new code'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
