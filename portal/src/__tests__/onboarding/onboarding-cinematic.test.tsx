import { createElement } from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { FormProvider, useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { profileSchema, type ProfileFormValues } from "@/app/onboarding/schemas"

// Polyfill ResizeObserver (Radix RadioGroup needs it)
globalThis.ResizeObserver ??= class {
  observe() {} unobserve() {} disconnect() {}
} as unknown as typeof ResizeObserver

// Override global framer-motion mock to add useReducedMotion
vi.mock("framer-motion", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, react/display-name
  const mc = (tag: string) => ({ children, ...p }: any) => createElement(tag, p, children)
  const motion = new Proxy({}, { get: (_: object, t: string) => mc(t) })
  return { motion, useInView: () => true, useReducedMotion: () => false,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children }
})

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn().mockResolvedValue({ status: "ok" }) }))
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
vi.mock("@/components/ui/slider", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Slider: (p: any) => createElement("input", { type: "range", "aria-label": p["aria-label"] }),
}))
vi.mock("@/app/onboarding/components/scroll-progress", () => ({
  ScrollProgress: () => createElement("div", { "data-testid": "scroll-progress" }),
}))
vi.mock("@/app/onboarding/components/ambient-particles", () => ({ AmbientParticles: () => null }))

import { OnboardingCinematic } from "@/app/onboarding/onboarding-cinematic"
import { ProfileSection } from "@/app/onboarding/sections/profile-section"

describe("OnboardingCinematic", () => {
  it("renders form with all five sections", () => {
    render(<OnboardingCinematic userId="u-test" />)
    expect(document.querySelector("form")).toBeInTheDocument()
    for (const label of ["The Score", "The Chapters", "The Rules", "Who Are You", "Your Mission"])
      expect(screen.getByLabelText(label)).toBeInTheDocument()
  })
})

function FormWrapper({ children }: { children: React.ReactNode }) {
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { location_city: "", social_scene: undefined, drug_tolerance: 3 },
  })
  return <FormProvider {...form}>{children}</FormProvider>
}

describe("ProfileSection", () => {
  it("renders form fields and Nikita quote", () => {
    render(<ProfileSection />, { wrapper: FormWrapper })
    expect(screen.getByTestId("section-profile")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("City, Country")).toBeInTheDocument()
    expect(screen.getByText("What's your scene?")).toBeInTheDocument()
    expect(screen.getByText("How edgy should I be?")).toBeInTheDocument()
    expect(screen.getByText(/Before we really get started/)).toBeInTheDocument()
  })
})
