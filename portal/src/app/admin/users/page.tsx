import { UserTable } from "@/components/admin/user-table"

export default function AdminUsersPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">User Management</h1>
      <UserTable />
    </div>
  )
}
