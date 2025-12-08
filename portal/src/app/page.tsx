'use client'

import { Suspense, useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { loginWithMagicLink } from '@/lib/supabase'

function LoginForm() {
  const searchParams = useSearchParams()
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [emailError, setEmailError] = useState<string | null>(null)

  // Check for auth callback errors in URL params
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

  const handleSubmit = async (e: React.FormEvent) => {
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
      const { error } = await loginWithMagicLink(email)

      if (error) {
        setMessage({
          type: 'error',
          text: error.message || 'Failed to send magic link. Please try again.',
        })
      } else {
        setMessage({
          type: 'success',
          text: 'Check your email for the magic link to sign in.',
        })
        setEmail('') // Clear email on success
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: 'An unexpected error occurred. Please try again.',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-background/95">
      <div className="w-full max-w-md space-y-6">
        {/* Logo/Title Area */}
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
            Nikita
          </h1>
          <p className="text-sm text-muted-foreground">
            Don&apos;t Get Dumped
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-semibold">Sign In</CardTitle>
            <CardDescription>
              Enter your email to receive a magic link
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
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

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? 'Sending...' : 'Send Magic Link'}
              </Button>
            </form>

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
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background via-background to-background/95">
        <div className="w-full max-w-md text-center">
          <div className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
            Nikita
          </div>
        </div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  )
}
