import { AppLayout } from "@/components/layout/sidebar"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <AppLayout variant="player">{children}</AppLayout>
}
