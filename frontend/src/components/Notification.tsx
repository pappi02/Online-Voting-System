import React, { useEffect } from 'react'

interface NotificationProps {
  type: 'info' | 'success' | 'error' | 'warning'
  message: string
  isVisible: boolean
  onClose: () => void
  duration?: number
}

export default function Notification({
  type,
  message,
  isVisible,
  onClose,
  duration = 5000
}: NotificationProps) {
  useEffect(() => {
    if (!isVisible) return

    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [isVisible, duration, onClose])

  if (!isVisible) return null

  return (
    <div className={`notification notification-${type}`}>
      <div className="notification-content">
        <span className="notification-icon">
          {type === 'success' && '✓'}
          {type === 'error' && '✕'}
          {type === 'info' && 'ℹ'}
          {type === 'warning' && '⚠'}
        </span>
        <span className="notification-message">{message}</span>
      </div>
      <button
        className="notification-close"
        onClick={onClose}
        aria-label="Close notification"
      >
        ✕
      </button>
    </div>
  )
}
