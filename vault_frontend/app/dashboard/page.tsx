'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { fetchApi, API_BASE } from '@/lib/api'
import { Dashboard } from '@/components/storage-dashboard'

type VaultFile = {
  file_id: string
  filename: string
  total_size: number
  total_chunks: number
  created_at: string
}

export default function DashboardPage() {
  const { isSignedIn, isLoaded, getToken } = useAuth()
  const router = useRouter()
  const [files, setFiles] = useState<VaultFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [activeShareUrl, setActiveShareUrl] = useState('')

  // Immediately redirect to /sign-in and clear memory when logged out
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      setFiles([])
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  const loadFiles = async () => {
    if (!isSignedIn) return
    try {
      setLoading(true)
      const token = await getToken()
      const data = await fetchApi('/files/', {}, token)
      setFiles(data?.files || [])
    } catch (err) {
      console.error('Failed to load files', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      loadFiles()
    }
  }, [isLoaded, isSignedIn])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      setIsUploading(true)
      const formData = new FormData()
      formData.append('file', file)

      const token = await getToken()
      const headers = new Headers()
      if (token) headers.set('Authorization', `Bearer ${token}`)

      const res = await fetch(`${API_BASE}/files/upload`, {
        method: 'POST',
        body: formData,
        headers,
      })

      if (!res.ok) throw new Error('Upload failed')
      await loadFiles()
    } catch (err) {
      console.error(err)
      alert('Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDelete = async (file_id: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/files/${file_id}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('Delete failed')
      await loadFiles()
    } catch (err) {
      console.error(err)
      alert('Failed to delete file')
    }
  }

  const handleRename = async (file_id: string, current_name: string) => {
    const new_name = prompt('Enter new filename:', current_name)
    if (!new_name || new_name === current_name) return
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/files/${file_id}/rename`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ name: new_name }),
      })
      if (!res.ok) throw new Error('Rename failed')
      await loadFiles()
    } catch (err) {
      console.error(err)
      alert('Failed to rename file')
    }
  }

  const handleShare = async (file_id: string) => {
    try {
      const token = await getToken()
      const res = await fetch(`${API_BASE}/files/${file_id}/share`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error('Share failed')
      const data = await res.json()
      const shareUrl = `${window.location.origin}/share/${data.share_id}`
      setActiveShareUrl(shareUrl)
      navigator.clipboard?.writeText(shareUrl)
    } catch (err) {
      console.error(err)
      alert('Failed to generate share link')
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const vaultFiles = files.map((f) => {
    const ext = f.filename.split('.').pop()?.toLowerCase() || ''
    let type = 'file'
    let color = 'zinc'
    if (['pdf'].includes(ext)) {
      type = 'pdf'
      color = 'violet'
    } else if (['fig'].includes(ext)) {
      type = 'fig'
      color = 'orange'
    } else if (['mp4', 'mov'].includes(ext)) {
      type = 'video'
      color = 'pink'
    } else if (['xlsx', 'csv'].includes(ext)) {
      type = 'sheet'
      color = 'emerald'
    } else if (['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) {
      type = 'file'
      color = 'blue'
    }

    return {
      ...f,
      size_formatted: formatBytes(f.total_size),
      type,
      color,
    }
  })

  // If not signed in yet or logging out, don't show any dashboard UI
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

  return (
    <Dashboard
      vaultFiles={vaultFiles}
      onUploadFiles={handleFileUpload}
      onDelete={handleDelete}
      onRename={handleRename}
      onShare={handleShare}
      isUploading={isUploading}
      activeShareUrl={activeShareUrl}
    />
  )
}
