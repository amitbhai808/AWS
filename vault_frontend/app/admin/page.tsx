'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { Admin } from '@/components/storage-dashboard'

export default function AdminPage() {
  const { isSignedIn, isLoaded } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0b0d11]">
        <div className="flex flex-col items-center gap-3">
          <div className="size-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
          <span className="text-xs text-zinc-500 font-mono">Redirecting to login...</span>
        </div>
      </div>
    )
  }

  return <Admin />
}
