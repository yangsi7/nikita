'use client'

import { Suspense, useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { sendOtpCode, verifyOtpCode, createClient } from '@/lib/supabase/client'

function LoginForm() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [step, setStep] = useState<'email' | 'otp'>('email')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [emailError, setEmailError] = useState<string | null>(null)
  const [otpError, setOtpError] = useState<string | null>(null)

  // Handle PKCE code exchange on page load
  // The Supabase browser client does NOT auto-detect codes - we must manually exchange
  useEffect(() => {
    const code = searchParams.get('code')

    if (code) {
      const exchangeCode = async () => {
        setIsLoading(true)
        try {
          const supabase = createClient()
          const { error } = await supabase.auth.exchangeCodeForSession(code)

          if (error) {
            console.error('[Login] PKCE code exchange failed:', error.message)
            setMessage({
              type: 'error',
              text: 'Authentication failed. Please try requesting a new magic link.',
            })
            // Clear the code from URL to prevent retry loops
            router.replace('/')
          } else {
            console.log('[Login] PKCE code exchange succeeded, redirecting to dashboard')
            // Success! Redirect to dashboard
            router.push('/dashboard')
          }
        } catch (err) {
          console.error('[Login] Unexpected error during code exchange:', err)
          setMessage({
            type: 'error',
            text: 'An unexpected error occurred. Please try again.',
          })
          router.replace('/')
        } finally {
          setIsLoading(false)
        }
      }

      exchangeCode()
    }
  }, [searchParams, router])

  // Handle auth callback errors in URL params
  useEffect(() => {
    const error = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    if (error) {
      setMessage({
        type: 'error',
        text: errorDescription || 'Authentication failed. Please try again.',
      })
    }
  }, [searchParams])

  const validateEmail = (email: string): boolean => {
    // RFC 5322 compliant email regex (simplified)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault()

    // Reset messages
    setMessage(null)
    setEmailError(null)

    // Validate email
    if (!email) {
      setEmailError('Email is required')
      return
    }

    if (!validateEmail(email)) {
      setEmailError('Please enter a valid email address')
      return
    }

    setIsLoading(true)

    try {
      const { error } = await sendOtpCode(email)

      if (error) {
        setMessage({
          type: 'error',
          text: error.message || 'Failed to send code. Please try again.',
        })
      } else {
        // Success! Move to OTP entry step
        setStep('otp')
        setMessage({
          type: 'success',
          text: `We sent a code to ${email}. Check your inbox.`,
        })
      }
    } catch {
      setMessage({
        type: 'error',
        text: 'An unexpected error occurred. Please try again.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault()

    // Reset messages
    setMessage(null)
    setOtpError(null)

    // Validate OTP code
    if (!otpCode) {
      setOtpError('Please enter the code from your email')
      return
    }

    if (!/^\d{6,8}$/.test(otpCode)) {
      setOtpError('Please enter a valid 6-8 digit code')
      return
    }

    setIsLoading(true)

    try {
      const { data, error } = await verifyOtpCode(email, otpCode)

      if (error) {
        // Handle specific error types
        if (error.message.includes('expired')) {
          setMessage({
            type: 'error',
            text: 'Code expired. Please request a new one.',
          })
        } else if (error.message.includes('invalid')) {
          setOtpError('Invalid code. Please check and try again.')
        } else {
          setMessage({
            type: 'error',
            text: error.message || 'Verification failed. Please try again.',
          })
        }
      } else if (data?.session) {
        // Success! Redirect to dashboard
        setMessage({
          type: 'success',
          text: 'Verified! Redirecting...',
        })
        router.push('/dashboard')
      } else {
        setMessage({
          type: 'error',
          text: 'Verification succeeded but no session was created. Please try again.',
        })
      }
    } catch {
      setMessage({
        type: 'error',
        text: 'An unexpected error occurred. Please try again.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleResendCode = async () => {
    setIsLoading(true)
    setMessage(null)
    setOtpError(null)
    setOtpCode('')

    try {
      const { error } = await sendOtpCode(email)

      if (error) {
        setMessage({
          type: 'error',
          text: error.message || 'Failed to resend code. Please try again.',
        })
      } else {
        setMessage({
          type: 'success',
          text: 'New code sent! Check your inbox.',
        })
      }
    } catch {
      setMessage({
        type: 'error',
        text: 'Failed to resend code. Please try again.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangeEmail = () => {
    setStep('email')
    setOtpCode('')
    setOtpError(null)
    setMessage(null)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-background/95">
      <div className="w-full max-w-md space-y-6">
        {/* Logo/Title Area */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
            Nikita
          </h1>
          <p className="text-sm text-muted-foreground">Don&apos;t Get Dumped</p>
        </div>

        {/* Login Card */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-semibold">Sign In</CardTitle>
            <CardDescription>
              {step === 'email'
                ? 'Enter your email to receive a verification code'
                : `Enter the code we sent to ${email}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Step 1: Email Entry */}
            {step === 'email' && (
              <form onSubmit={handleSendOtp} className="space-y-4">
                <div className="space-y-2">
                  <Input
                    type="email"
                    placeholder="your.email@example.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      setEmailError(null)
                    }}
                    disabled={isLoading}
                    className={`${emailError ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                    aria-invalid={!!emailError}
                    aria-describedby={emailError ? 'email-error' : undefined}
                  />
                  {emailError && (
                    <p id="email-error" className="text-sm text-destructive">
                      {emailError}
                    </p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? 'Sending...' : 'Send Code'}
                </Button>
              </form>
            )}

            {/* Step 2: OTP Entry */}
            {step === 'otp' && (
              <form onSubmit={handleVerifyOtp} className="space-y-4">
                <div className="space-y-2">
                  <Input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={8}
                    placeholder="123456"
                    value={otpCode}
                    onChange={(e) => {
                      // Only allow digits
                      const value = e.target.value.replace(/\D/g, '')
                      setOtpCode(value)
                      setOtpError(null)
                    }}
                    disabled={isLoading}
                    className={`text-center text-2xl tracking-[0.5em] font-mono ${otpError ? 'border-destructive focus-visible:ring-destructive' : ''}`}
                    aria-invalid={!!otpError}
                    aria-describedby={otpError ? 'otp-error' : undefined}
                    autoFocus
                  />
                  {otpError && (
                    <p id="otp-error" className="text-sm text-destructive">
                      {otpError}
                    </p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading ? 'Verifying...' : 'Verify Code'}
                </Button>

                <div className="flex justify-between items-center text-sm">
                  <button
                    type="button"
                    onClick={handleResendCode}
                    disabled={isLoading}
                    className="text-primary hover:underline disabled:opacity-50"
                  >
                    Resend code
                  </button>
                  <button
                    type="button"
                    onClick={handleChangeEmail}
                    disabled={isLoading}
                    className="text-muted-foreground hover:text-foreground disabled:opacity-50"
                  >
                    Use different email
                  </button>
                </div>
              </form>
            )}

            {/* Success/Error Messages */}
            {message && (
              <div
                className={`mt-4 p-3 rounded-md text-sm ${
                  message.type === 'success'
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'bg-destructive/10 text-destructive border border-destructive/20'
                }`}
                role="alert"
              >
                {message.text}
              </div>
            )}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <div className="text-sm text-muted-foreground text-center">
              New user?{' '}
              <span className="text-primary hover:underline cursor-pointer">
                Connect your Telegram first
              </span>
            </div>
            <div className="text-xs text-muted-foreground/60 text-center">
              By signing in, you agree to play the game at your own emotional risk
            </div>
          </CardFooter>
        </Card>

        {/* Footer hint */}
        <p className="text-center text-xs text-muted-foreground/50">
          She&apos;s waiting for you...
        </p>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-background/95">
          <div className="w-full max-w-md text-center">
            <div className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
              Nikita
            </div>
          </div>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  )
}
