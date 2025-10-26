import { NextResponse } from "next/server"
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import Stripe from 'stripe'
import { z } from 'zod'

const BodySchema = z.object({
  priceId: z.string(),
  user: z.object({
    id: z.string(),
    email: z.string().email().optional(),
  }).optional(),
})

type CheckoutBody = z.infer<typeof BodySchema>

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

export async function POST(req: Request) {
  try {
    const session: any = await getServerSession(authOptions)
    
    // Check if session and user exist with explicit typing
    if (!session || !session.user || !session.user.email) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      )
    }

    // Parse request body with proper Zod validation and error handling
    const json = await req.json().catch(() => ({}))
    const parse = BodySchema.safeParse(json)
    
    if (!parse.success) {
      return NextResponse.json({ error: "Invalid body" }, { status: 400 })
    }
    
    const { priceId, user } = parse.data
    
    const finalPriceId = priceId || process.env.STRIPE_PRICE_PRO

    if (!finalPriceId) {
      return NextResponse.json(
        { error: 'Price ID is required' },
        { status: 400 }
      )
    }

    // Get user info from session with explicit typing
    const userEmail: string = session.user.email
    const userId: string = user?.id || session.user.id || userEmail
    const orgId: string = session.user.orgId || 'default'

    // Create Stripe checkout session
    const checkoutSession = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: finalPriceId,
          quantity: 1,
        },
      ],
      success_url: `${process.env.NEXTAUTH_URL}/dashboard?success=true`,
      cancel_url: `${process.env.NEXTAUTH_URL}/pricing?canceled=true`,
      customer_email: userEmail,
      metadata: {
        userId: userId,
        orgId: orgId,
      },
    })

    return NextResponse.json({ url: checkoutSession.url })
  } catch (error: any) {
    console.error('Stripe checkout error:', error)
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    )
  }
}