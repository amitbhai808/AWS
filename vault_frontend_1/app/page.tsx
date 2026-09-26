import { redirect } from 'next/navigation'

export default function Page() {
  redirect('/dashboard')
}

export const dynamic = 'force-dynamic'

// Dashboard is the default workspace route.

