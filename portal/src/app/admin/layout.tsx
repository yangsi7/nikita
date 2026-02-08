import { AppLayout } from "@/components/layout/sidebar"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AppLayout variant="admin">{children}</AppLayout>
}
