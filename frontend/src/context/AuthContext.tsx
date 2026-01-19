import React, { createContext, useContext, useState } from 'react'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  status: 'pending' | 'verified' | 'eligible' | 'ineligible'
  joinDate: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => void
  signup: (firstName: string, lastName: string, email: string, password: string) => void
  logout: () => void
  generateOTP: (email: string) => string
  verifyOTP: (email: string, code: string) => boolean
  completeSignup: (firstName: string, lastName: string, email: string, password: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface OTPData {
  code: string
  expiresAt: number
}

const otpStore: { [key: string]: OTPData } = {}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  const generateOTP = (email: string) => {
    const code = Math.floor(100000 + Math.random() * 900000).toString()
    const expiresAt = Date.now() + 5 * 60 * 1000 // 5 minutes
    otpStore[email] = { code, expiresAt }
    console.log(`OTP for ${email}: ${code}`) // In production, this would be sent via email service
    return code
  }

  const verifyOTP = (email: string, code: string) => {
    const otpData = otpStore[email]
    if (!otpData) return false
    if (Date.now() > otpData.expiresAt) {
      delete otpStore[email]
      return false
    }
    if (otpData.code !== code) return false
    delete otpStore[email]
    return true
  }

  const login = (email: string, password: string) => {
    // Mock login
    const mockUser: User = {
      id: '12345',
      email,
      firstName: 'John',
      lastName: 'Doe',
      status: 'verified',
      joinDate: new Date().toISOString().split('T')[0]
    }
    setUser(mockUser)
  }

  const signup = (firstName: string, lastName: string, email: string, password: string) => {
    // This is called when OTP verification is successful
    const mockUser: User = {
      id: Math.random().toString(36).substr(2, 9),
      email,
      firstName,
      lastName,
      status: 'verified',
      joinDate: new Date().toISOString().split('T')[0]
    }
    setUser(mockUser)
  }

  const completeSignup = (firstName: string, lastName: string, email: string, password: string) => {
    // Save to database (mock) - called after OTP verification
    signup(firstName, lastName, email, password)
  }

  const logout = () => {
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, logout, generateOTP, verifyOTP, completeSignup }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
