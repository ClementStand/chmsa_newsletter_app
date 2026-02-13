'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface RefreshStatus {
  status: 'idle' | 'running' | 'completed' | 'error'
  current_competitor?: string
  processed: number
  total: number
  percent_complete: number
  estimated_seconds_remaining?: number
  error?: string
}

export function DashboardRefreshButton() {
  const router = useRouter()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [status, setStatus] = useState<RefreshStatus | null>(null)
  const [showSuccess, setShowSuccess] = useState(false)

  // Poll status while refreshing
  useEffect(() => {
    if (!isRefreshing) return

    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch('/api/refresh/status')
        const data = await res.json()
        setStatus(data)

        if (data.status === 'completed') {
          setIsRefreshing(false)
          setShowSuccess(true)
          router.refresh()

          // Hide success message after 3 seconds
          setTimeout(() => setShowSuccess(false), 3000)
        } else if (data.status === 'error') {
          setIsRefreshing(false)
        }
      } catch (error) {
        console.error('Status polling failed:', error)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [isRefreshing, router])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    setShowSuccess(false)
    try {
      const res = await fetch('/api/refresh', { method: 'POST' })
      if (!res.ok) {
        throw new Error('Refresh failed')
      }
    } catch (error) {
      console.error('Refresh failed:', error)
      setIsRefreshing(false)
      setStatus({
        status: 'error',
        processed: 0,
        total: 0,
        percent_complete: 0,
        error: 'Failed to start refresh'
      })
    }
  }

  return (
    <div className="space-y-3">
      <Button
        onClick={handleRefresh}
        disabled={isRefreshing}
        size="lg"
        className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <RefreshCw className={`mr-2 h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
        {isRefreshing ? 'Scanning Networks...' : 'Scan for New Intel'}
      </Button>

      {/* Progress Display */}
      {isRefreshing && status && (
        <div className="space-y-2 bg-slate-900 border border-slate-800 rounded-lg p-4 animate-in fade-in slide-in-from-top-2">
          <div className="flex justify-between text-sm text-slate-400">
            <span className="truncate max-w-[200px]">
              {status.current_competitor ? `Processing ${status.current_competitor}...` : 'Starting scan...'}
            </span>
            <span className="text-slate-500">{status.processed} / {status.total || '?'}</span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-500 to-cyan-400 h-full transition-all duration-500 ease-out"
              style={{ width: `${status.percent_complete || 0}%` }}
            />
          </div>

          {status.estimated_seconds_remaining && status.estimated_seconds_remaining > 0 && (
            <div className="text-xs text-slate-500 text-center">
              Est. {Math.ceil(status.estimated_seconds_remaining / 60)} min remaining
            </div>
          )}
        </div>
      )}

      {/* Success Message */}
      {showSuccess && (
        <div className="flex items-center gap-2 bg-emerald-900/30 border border-emerald-700 rounded-lg p-3 text-sm text-emerald-400 animate-in fade-in slide-in-from-top-2">
          <CheckCircle className="h-4 w-4" />
          <span>Intelligence scan complete!</span>
        </div>
      )}

      {/* Error Message */}
      {status?.status === 'error' && !isRefreshing && (
        <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-400 animate-in fade-in slide-in-from-top-2">
          <AlertCircle className="h-4 w-4" />
          <span>{status.error || 'Scan failed. Please try again.'}</span>
        </div>
      )}
    </div>
  )
}
