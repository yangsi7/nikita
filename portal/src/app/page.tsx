import type { Metadata } from "next"
import { createClient } from "@/lib/supabase/server"
import { HeroSection } from "@/components/landing/hero-section"
import { PitchSection } from "@/components/landing/pitch-section"
import { PortalShowcase } from "@/components/landing/portal-showcase"
import { StakesSection } from "@/components/landing/stakes-section"
import { CtaSection } from "@/components/landing/cta-section"
import { LandingNav } from "@/components/landing/landing-nav"

// Page-level OG metadata — overrides layout.tsx for root `/` only
// Do NOT move to layout.tsx (it would propagate to dashboard, admin, login)
export const metadata: Metadata = {
  title: "Nikita — Don't Get Dumped",
  description:
    "She remembers everything. She has her own life. And she will leave you. 5 chapters. 3 strikes. One relationship.",
  openGraph: {
    title: "Nikita — Don't Get Dumped",
    description:
      "She remembers everything. She has her own life. And she will leave you.",
    images: ["/opengraph-image.png"],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
}

export default async function LandingPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  const isAuthenticated = !!user

  return (
    <main className="bg-void min-h-screen">
      <LandingNav isAuthenticated={isAuthenticated} />
      <HeroSection isAuthenticated={isAuthenticated} />
      <PitchSection />
      <PortalShowcase />
      <StakesSection />
      <CtaSection isAuthenticated={isAuthenticated} />
    </main>
  )
}
