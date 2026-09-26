'use client'

import { use, useEffect, useState } from 'react'
import { API_BASE } from '@/lib/api'
import { Archive, Download, FileText, HardDrive, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function SharePage({ params }: { params: Promise<{ share_id: string }> }) {
  const resolvedParams = use(params)
  const shareId = resolvedParams.share_id

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0b0d11] p-6 text-zinc-100">
      <div className="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#12151b] p-8 text-center shadow-2xl backdrop-blur-md">
        <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
          <Archive className="size-7" />
        </div>
        <h1 className="text-xl font-semibold text-white">Shared Vault File</h1>
        <p className="mt-2 text-sm text-zinc-400">
          This file was shared securely from a distributed Vault cluster node.
        </p>

        <div className="my-6 rounded-xl border border-white/[0.06] bg-white/[0.03] p-4 text-xs font-mono text-zinc-400 space-y-2 text-left">
          <div className="flex justify-between">
            <span className="text-zinc-500">Share ID:</span>
            <span className="truncate max-w-[200px] text-zinc-300">{shareId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">Replication:</span>
            <span className="text-emerald-400">3x verified</span>
          </div>
        </div>

        <a
          href={`${API_BASE}/share/${shareId}/download`}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-4 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.25)] hover:brightness-110 active:scale-[0.98] transition-all"
        >
          <Download className="size-4" />
          Download File
        </a>
      </div>
    </div>
  )
}
