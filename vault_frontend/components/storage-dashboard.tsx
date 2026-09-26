'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity, Archive, ArrowUpRight, BarChart3, Bell, CheckCircle2,
  ChevronDown, Clock, Copy, Cpu, Database, ExternalLink, File,
  FileCode2, FileImage, FileText, Folder, HardDrive, Layers, LayoutGrid,
  Menu, MoreHorizontal, Plus, Radio, Search, Server, Settings2,
  Share2, ShieldCheck, Sparkles, Trash2, UploadCloud, Users, Wifi, X, Zap
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { API_BASE, fetchApi } from '@/lib/api'
import { UserButton, useAuth } from '@clerk/nextjs'

const nav = [
  { href: '/dashboard', label: 'My files', icon: LayoutGrid, count: null },
  { href: '/simulator', label: 'Storage simulator', icon: Activity, count: 'Live' },
  { href: '/admin', label: 'Admin console', icon: ShieldCheck, count: null },
]

const collections = [
  { label: 'Starred', icon: Sparkles, iconColor: 'text-amber-400', badge: '3' },
  { label: 'Shared with me', icon: Share2, iconColor: 'text-violet-400', badge: '8' },
  { label: 'Recent activity', icon: Clock, iconColor: 'text-sky-400', badge: null },
  { label: 'Trash & Retention', icon: Trash2, iconColor: 'text-zinc-500', badge: null },
]

const nodes = [
  { port: '8001', status: 'healthy' },
  { port: '8002', status: 'healthy' },
  { port: '8003', status: 'healthy' },
  { port: '8004', status: 'healthy' },
]

interface SidebarProps {
  onUpload?: () => void
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

function Sidebar({ onUpload, mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname()

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between overflow-y-auto p-4 custom-scrollbar">
      {/* Top section */}
      <div className="space-y-6">
        {/* Brand / Logo */}
        <div className="flex items-center justify-between px-2 pt-1">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 text-slate-950 font-bold shadow-[0_0_20px_rgba(34,211,238,0.35)] transition-transform group-hover:scale-105">
              <Archive className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-sm font-semibold tracking-wide text-white">
                vault<span className="text-cyan-400">.io</span>
                <span className="rounded-full bg-cyan-500/10 px-1.5 py-0.5 text-[9px] font-mono font-medium text-cyan-400 border border-cyan-500/20">
                  v0.1
                </span>
              </div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500 font-medium">
                distributed storage
              </div>
            </div>
          </Link>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/[0.08] hover:text-white lg:hidden"
            >
              <X className="size-5" />
            </button>
          )}
        </div>

        {/* Quick Action Button */}
        {onUpload && (
          <button
            onClick={() => {
              if (onCloseMobile) onCloseMobile()
              onUpload()
            }}
            className="group relative flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-2.5 px-4 text-xs font-semibold text-slate-950 shadow-[0_0_22px_rgba(34,211,238,0.25)] transition-all hover:brightness-110 active:scale-[0.98]"
          >
            <UploadCloud className="size-4 transition-transform group-hover:-translate-y-0.5" />
            <span>New Upload</span>
          </button>
        )}

        {/* Navigation - Workspace */}
        <div>
          <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Workspace
          </div>
          <nav className="flex flex-col gap-1">
            {nav.map(({ href, label, icon: Icon, count }) => {
              const active = pathname === href
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onCloseMobile}
                  className={`group flex items-center justify-between rounded-xl px-3 py-2 text-sm font-medium transition-all ${
                    active
                      ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 shadow-sm'
                      : 'text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-200'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`size-4 ${active ? 'text-cyan-400' : 'text-zinc-500 group-hover:text-zinc-300'}`} />
                    <span>{label}</span>
                  </div>
                  {count === 'Live' ? (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full border border-emerald-500/20">
                      <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Live
                    </span>
                  ) : null}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Navigation - Collections */}
        <div>
          <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
            Collections & Tags
          </div>
          <div className="flex flex-col gap-1">
            {collections.map(({ label, icon: Icon, iconColor, badge }) => (
              <button
                key={label}
                className="group flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm text-zinc-400 transition-colors hover:bg-white/[0.04] hover:text-zinc-200"
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`size-4 ${iconColor} opacity-80 group-hover:opacity-100`} />
                  <span className="text-zinc-400 group-hover:text-zinc-200">{label}</span>
                </div>
                {badge && (
                  <span className="rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-medium text-zinc-400">
                    {badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Cluster Telemetry & Swarm Status (Extra Info) */}
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.025] p-3.5 backdrop-blur-md">
          <div className="mb-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Server className="size-3.5 text-cyan-400" />
              <span>Cluster Swarm</span>
            </div>
            <span className="flex items-center gap-1 text-[10px] font-mono font-medium text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full border border-emerald-500/20">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
              4/4 Online
            </span>
          </div>

          {/* Node port matrix */}
          <div className="grid grid-cols-2 gap-1.5 mb-3">
            {nodes.map((node) => (
              <div
                key={node.port}
                className="flex items-center justify-between rounded-lg border border-white/[0.05] bg-black/40 px-2 py-1 text-[11px] font-mono"
              >
                <span className="text-zinc-400">:{node.port}</span>
                <span className="size-1.5 rounded-full bg-emerald-400" />
              </div>
            ))}
          </div>

          <div className="space-y-1.5 border-t border-white/[0.06] pt-2.5 text-[10px] text-zinc-400">
            <div className="flex justify-between">
              <span className="text-zinc-500">Replication:</span>
              <span className="font-mono text-zinc-300">3x Copies</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Hash Ring:</span>
              <span className="font-mono text-zinc-300">SHA-256 (100 vn)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Auto-Healing:</span>
              <span className="text-emerald-400">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom section: Storage Quota & Capacity */}
      <div className="mt-6 space-y-3">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-3.5 backdrop-blur-md">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="font-medium text-zinc-300">Cluster Storage</span>
            <span className="font-mono font-semibold text-cyan-400">6.8%</span>
          </div>
          <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-white/[0.08]">
            <div className="h-full w-[6.8%] rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 shadow-[0_0_8px_rgba(34,211,238,0.5)]" />
          </div>
          <div className="flex items-center justify-between text-[11px] text-zinc-400">
            <span>680 MB used</span>
            <span className="text-zinc-600">of 10 GB</span>
          </div>
          <Link
            href="/simulator"
            onClick={onCloseMobile}
            className="mt-2.5 flex items-center justify-between text-[11px] font-medium text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <span>Ring distribution</span>
            <ArrowUpRight className="size-3" />
          </Link>
        </div>

        {/* System Latency Badge */}
        <div className="flex items-center justify-between px-2 text-[10px] text-zinc-600">
          <div className="flex items-center gap-1.5">
            <Wifi className="size-3 text-emerald-500" />
            <span>Gateway latency: 1.2ms</span>
          </div>
          <span>Local cluster</span>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-white/[0.07] bg-[#101217]/95 lg:flex lg:flex-col h-screen sticky top-0">
        {sidebarContent}
      </aside>

      {/* Mobile Slide-over Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <aside className="fixed inset-y-0 left-0 w-72 max-w-[85vw] border-r border-white/[0.1] bg-[#101217] shadow-2xl transition-transform">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  )
}

function Header({ onUpload, onToggleMenu }: { onUpload: () => void; onToggleMenu?: () => void }) {
  return (
    <header className="flex h-20 items-center gap-3 border-b border-white/[0.07] px-5 sm:px-8">
      <button
        onClick={onToggleMenu}
        aria-label="Open navigation menu"
        className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/[0.06] hover:text-white lg:hidden"
      >
        <Menu className="size-5" />
      </button>

      <div className="relative max-w-md flex-1">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500" />
        <input
          className="h-10 w-full rounded-xl border border-white/[0.08] bg-white/[0.035] pl-10 pr-4 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-cyan-300/40"
          placeholder="Search files and folders"
        />
      </div>

      <button className="hidden size-9 items-center justify-center rounded-xl text-zinc-500 hover:bg-white/[0.05] sm:flex">
        <Bell className="size-4" />
      </button>

      <div className="flex items-center gap-2 border-l border-white/[0.08] pl-3">
        <UserButton />
      </div>
    </header>
  )
}

function UploadDialog({
  onClose,
  onUploadFiles,
  isUploading,
}: {
  onClose: () => void
  onUploadFiles: (e: any) => void
  isUploading: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-white/[0.1] bg-[#15181e] p-6 shadow-2xl">
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Upload files</h2>
            <p className="mt-1 text-sm text-zinc-500">Add files to your distributed vault.</p>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white">
            <X className="size-5" />
          </button>
        </div>
        <div className="relative flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-cyan-300/30 bg-cyan-300/[0.03] hover:border-cyan-300 hover:bg-cyan-300/[0.05] transition-colors">
          <input
            type="file"
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => {
              onUploadFiles(e)
              onClose()
            }}
            disabled={isUploading}
          />
          <UploadCloud className="mb-3 size-8 text-cyan-300" />
          <div className="text-sm text-zinc-300">
            Drop files here or <span className="text-cyan-300">browse</span>
          </div>
          <div className="mt-1 text-xs text-zinc-600">Up to 5 GB per file</div>
        </div>
        {isUploading && (
          <div className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">
            <div className="flex items-center gap-3">
              <FileText className="size-5 text-violet-300" />
              <div className="flex-1">
                <div className="text-xs text-zinc-300">Uploading chunks...</div>
                <div className="mt-2 h-1 overflow-hidden rounded bg-white/[0.08]">
                  <div className="h-full w-3/4 rounded bg-cyan-300 animate-pulse" />
                </div>
              </div>
              <span className="text-xs text-cyan-300">Uploading...</span>
            </div>
          </div>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  )
}

function FileIcon({ type, color }: { type: string; color: string }) {
  const Icon = type === 'folder' ? Folder : type === 'pdf' || type === 'sheet' ? FileText : type === 'fig' ? FileCode2 : FileImage
  return (
    <div className={`flex size-11 items-center justify-center rounded-xl bg-${color}-400/10`}>
      <Icon className={`size-5 text-${color}-300`} />
    </div>
  )
}

function FileCard({
  file,
  onShare,
  onRename,
  onDelete,
}: {
  file: any
  onShare: () => void
  onRename: () => void
  onDelete: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="group relative rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3 transition-all hover:-translate-y-0.5 hover:border-cyan-300/25 hover:bg-white/[0.045]">
      <div className="mb-5 flex h-28 items-center justify-center rounded-xl bg-gradient-to-br from-white/[0.05] to-transparent">
        <FileIcon type={file.type} color={file.color} />
      </div>
      <div className="flex items-center gap-2">
        <FileIcon type={file.type} color={file.color} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-medium text-zinc-200">{file.filename}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600">{file.size_formatted}</div>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg p-1 text-zinc-600 hover:bg-white/[0.08] hover:text-white"
        >
          <MoreHorizontal className="size-4" />
        </button>
      </div>
      {open && (
        <div className="absolute right-3 top-36 z-10 w-32 rounded-xl border border-white/10 bg-[#1b1e25] p-1 shadow-xl">
          <a
            href={`${API_BASE}/files/${file.file_id}/download`}
            download={file.filename}
            target="_blank"
            rel="noreferrer"
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"
          >
            <Archive className="size-3.5" />
            Download
          </a>
          <button
            onClick={() => {
              setOpen(false)
              onShare()
            }}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"
          >
            <Share2 className="size-3.5" />
            Share
          </button>
          <button
            onClick={() => {
              setOpen(false)
              onRename()
            }}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/[0.07]"
          >
            <FileText className="size-3.5" />
            Rename
          </button>
          <button
            onClick={() => {
              setOpen(false)
              onDelete()
            }}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-red-300 hover:bg-red-400/10"
          >
            <X className="size-3.5" />
            Delete
          </button>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, note, icon: Icon }: { label: string; value: string; note: string; icon: typeof File }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs text-zinc-500">{label}</span>
        <Icon className="size-4 text-zinc-600" />
      </div>
      <div className="text-xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-[11px] text-emerald-300">{note}</div>
    </div>
  )
}

function ShareDialog({ onClose, activeShareUrl }: { onClose: () => void; activeShareUrl: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-white/[0.1] bg-[#15181e] p-6">
        <div className="mb-5 flex justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Share file</h2>
            <p className="mt-1 text-sm text-zinc-500">Anyone with this link can view.</p>
          </div>
          <button onClick={onClose} className="text-zinc-500">
            <X className="size-5" />
          </button>
        </div>
        <div className="flex gap-2">
          <input
            readOnly
            value={activeShareUrl}
            className="min-w-0 flex-1 rounded-lg border border-white/[0.1] bg-white/[0.04] px-3 text-sm text-zinc-300 outline-none font-mono text-xs"
          />
          <Button
            onClick={() => {
              setCopied(true)
              navigator.clipboard?.writeText(activeShareUrl)
            }}
            variant="outline"
            className="border-white/10 text-zinc-300"
          >
            {copied ? 'Copied' : <><Copy data-icon="inline-start" className="mr-1.5 size-3.5" />Copy</>}
          </Button>
        </div>
      </div>
    </div>
  )
}

function Shell({ children, onUpload }: { children: React.ReactNode; onUpload?: () => void }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#0b0d11] text-zinc-100 flex">
      <Sidebar
        onUpload={onUpload}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onUpload={onUpload ?? (() => {})} onToggleMenu={() => setMobileMenuOpen(true)} />
        <main className="flex-1 p-5 sm:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}

function Dashboard({
  vaultFiles,
  onUploadFiles,
  onDelete,
  onShare,
  onRename,
  isUploading,
  activeShareUrl,
}: any) {
  const [upload, setUpload] = useState(false)
  const [share, setShare] = useState(false)

  return (
    <Shell onUpload={() => setUpload(true)}>
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 text-xs text-zinc-600">
              <span>Workspace</span>
              <span>/</span>
              <span className="text-zinc-400">My files</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Storage Vault <span className="text-cyan-400">✦</span>
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              Distributed object storage with automatic replication across 4 active nodes.
            </p>
          </div>
          <Button
            onClick={() => setUpload(true)}
            className="w-fit bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-semibold hover:brightness-110 shadow-[0_0_20px_rgba(34,211,238,0.25)]"
          >
            <Plus data-icon="inline-start" className="mr-1.5 size-4" />
            New upload
          </Button>
        </div>

        <div className="mb-8 grid gap-3 sm:grid-cols-3">
          <Stat
            label="Total files"
            value={vaultFiles?.length ? String(vaultFiles.length) : '0'}
            note="Synchronized across cluster"
            icon={File}
          />
          <Stat
            label="Replication Factor"
            value="3x"
            note="Quorum-enforced durability"
            icon={ShieldCheck}
          />
          <Stat
            label="Active Storage Nodes"
            value="4 / 4"
            note="100% Ring Health"
            icon={HardDrive}
          />
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Files in Vault</h2>
          <span className="text-xs text-zinc-500 font-mono">
            {vaultFiles?.length || 0} file{vaultFiles?.length === 1 ? '' : 's'}
          </span>
        </div>

        {!vaultFiles || vaultFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.015] py-16 text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-400 mb-4 border border-cyan-500/20">
              <UploadCloud className="size-7" />
            </div>
            <h3 className="text-base font-semibold text-white">No files in your vault yet</h3>
            <p className="mt-1 text-sm text-zinc-500 max-w-sm">
              Upload documents, media, or archives to distribute chunks across the 4-node swarm.
            </p>
            <Button
              onClick={() => setUpload(true)}
              className="mt-6 bg-cyan-400 text-slate-950 font-semibold hover:bg-cyan-300"
            >
              <Plus className="mr-1.5 size-4" />
              Upload your first file
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {vaultFiles.map((file: any) => (
              <FileCard
                key={file.file_id}
                file={file}
                onShare={() => {
                  setShare(true)
                  onShare(file.file_id)
                }}
                onRename={() => onRename(file.file_id, file.filename)}
                onDelete={() => onDelete(file.file_id)}
              />
            ))}
          </div>
        )}
      </div>

      {upload && (
        <UploadDialog
          onClose={() => setUpload(false)}
          onUploadFiles={onUploadFiles}
          isUploading={isUploading}
        />
      )}
      {share && (
        <ShareDialog
          onClose={() => setShare(false)}
          activeShareUrl={activeShareUrl}
        />
      )}
    </Shell>
  )
}

function Simulator() {
  const [clusterStatus, setClusterStatus] = useState<any>(null)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await fetchApi('/cluster/status')
        if (data) setClusterStatus(data)
      } catch (err) {
        console.error(err)
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const simNodes = clusterStatus?.nodes || [
    { node_url: 'http://localhost:8001', is_healthy: true, storage_used_bytes: 42800000 },
    { node_url: 'http://localhost:8002', is_healthy: true, storage_used_bytes: 39200000 },
    { node_url: 'http://localhost:8003', is_healthy: true, storage_used_bytes: 41600000 },
    { node_url: 'http://localhost:8004', is_healthy: true, storage_used_bytes: 38400000 },
  ]

  return (
    <Shell>
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <div className="mb-3 text-xs text-zinc-600">Infrastructure / Storage simulator</div>
            <h1 className="text-2xl font-semibold text-white">Storage simulator</h1>
            <p className="mt-1 text-sm text-zinc-500">Monitor the distributed storage ring in real time.</p>
          </div>
          <Button variant="outline" className="border-white/10 text-zinc-300">
            <Activity data-icon="inline-start" className="mr-1.5 size-4" />
            Refresh
          </Button>
        </div>
        <div className="mb-6 grid gap-3 sm:grid-cols-3">
          <Stat
            label="Cluster health"
            value={`${clusterStatus?.active_nodes ?? 4} of ${clusterStatus?.nodes?.length ?? 4} active`}
            note="100% Swarm Availability"
            icon={Activity}
          />
          <Stat
            label="Total chunks"
            value={clusterStatus?.total_chunks ? String(clusterStatus.total_chunks) : '4,634'}
            note="Replicated across swarm"
            icon={Archive}
          />
          <Stat
            label="Replication factor"
            value={`${clusterStatus?.replication_factor ?? 3}x`}
            note="Quorum-enforced durability"
            icon={ShieldCheck}
          />
        </div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Storage nodes</h2>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <span className="size-1.5 rounded-full bg-emerald-400" />
            Live telemetry
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {simNodes.map((node: any, idx: number) => {
            const port = node.node_url ? node.node_url.split(':').pop() : `800${idx + 1}`
            const isHealthy = node.is_healthy ?? true
            const used = `${((node.storage_used_bytes || 0) / (1024 * 1024)).toFixed(1)} MB`
            const colors = ['cyan', 'emerald', 'violet', 'blue']
            const color = colors[idx % colors.length]

            return (
              <div key={port} className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`flex size-10 items-center justify-center rounded-xl bg-${color}-400/10 font-mono text-xs text-${color}-300`}>
                      :{port}
                    </div>
                    <div>
                      <div className="font-medium text-white">Node {port}</div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
                        <span className={`size-1.5 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        {isHealthy ? 'Active' : 'Offline'}
                      </div>
                    </div>
                  </div>
                  <button className="text-zinc-600 hover:text-white">
                    <Settings2 className="size-4" />
                  </button>
                </div>
                <div className="mt-6 grid grid-cols-2 gap-4 border-t border-white/[0.07] pt-4">
                  <div>
                    <div className="text-xs text-zinc-600">Storage used</div>
                    <div className="mt-1 text-lg text-zinc-200">{used}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-600">Health status</div>
                    <div className="mt-1 text-lg text-emerald-400">{isHealthy ? 'Online' : 'Failover'}</div>
                  </div>
                </div>
                <div className="mt-4 h-1 overflow-hidden rounded-full bg-white/[0.07]">
                  <div
                    className={`h-full rounded-full bg-${color}-300`}
                    style={{ width: `${60 + (idx * 5)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </Shell>
  )
}

function Admin() {
  return (
    <Shell>
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <div className="mb-3 text-xs text-zinc-600">System / Admin console</div>
          <h1 className="text-2xl font-semibold text-white">Admin console</h1>
          <p className="mt-1 text-sm text-zinc-500">Manage users, capacity, and system health.</p>
        </div>
        <div className="mb-8 grid gap-3 sm:grid-cols-3">
          <Stat label="System utilization" value="68.0%" note="Within healthy limits" icon={BarChart3} />
          <Stat label="Active users" value="248" note="+18 this month" icon={Users} />
          <Stat label="System uptime" value="99.98%" note="Last 30 days" icon={Activity} />
        </div>
        <div className="overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.025]">
          <div className="flex items-center justify-between border-b border-white/[0.07] p-5">
            <h2 className="text-sm font-semibold text-white">System users</h2>
            <Button variant="outline" className="border-white/10 text-zinc-300">
              <Users data-icon="inline-start" className="mr-1.5 size-4" />
              Invite user
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-white/[0.06] text-[11px] uppercase tracking-wider text-zinc-600">
                <tr>
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Role</th>
                  <th className="px-5 py-3 font-medium">Storage</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {[
                  ['Jordan Davis', 'admin@admin.com', 'Admin', '680 GB', 'Active'],
                  ['Maya Chen', 'maya@acme.co', 'Member', '124 GB', 'Active'],
                  ['Liam Jones', 'liam@acme.co', 'Member', '89 GB', 'Active'],
                  ['Noah Wilson', 'noah@acme.co', 'Viewer', '12 GB', 'Pending'],
                ].map(([name, email, role, storage, status]) => (
                  <tr key={email} className="text-zinc-300">
                    <td className="px-5 py-4">
                      <div className="font-medium text-zinc-200">{name}</div>
                      <div className="mt-0.5 text-xs text-zinc-600">{email}</div>
                    </td>
                    <td className="px-5 py-4 text-xs text-zinc-400">{role}</td>
                    <td className="px-5 py-4 text-xs text-zinc-400">{storage}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full px-2 py-1 text-[10px] ${
                          status === 'Active'
                            ? 'bg-emerald-400/10 text-emerald-300'
                            : 'bg-amber-400/10 text-amber-300'
                        }`}
                      >
                        {status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <MoreHorizontal className="ml-auto size-4 text-zinc-600" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Shell>
  )
}

export { Dashboard, Simulator, Admin, Sidebar, Shell }
export default Dashboard
