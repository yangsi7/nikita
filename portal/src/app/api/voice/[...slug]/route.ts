import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL =
  process.env.BACKEND_URL || 'https://nikita-api-1040094048579.us-central1.run.app'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> }
) {
  const { slug } = await params
  const path = slug.join('/')

  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/voice/${path}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('[Voice Proxy] GET error:', error)
    return NextResponse.json({ detail: 'Failed to reach backend' }, { status: 502 })
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> }
) {
  const { slug } = await params
  const path = slug.join('/')

  try {
    const body = await request.json()

    const response = await fetch(`${BACKEND_URL}/api/v1/voice/${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('[Voice Proxy] POST error:', error)
    return NextResponse.json({ detail: 'Failed to reach backend' }, { status: 502 })
  }
}
