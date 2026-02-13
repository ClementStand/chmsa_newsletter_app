'use client'

import { format } from 'date-fns'
import { CompetitorLogo } from './CompetitorLogo'
import { useState } from 'react'
import { Star, ExternalLink } from 'lucide-react'
import { cn } from "@/lib/utils"

export default function NewsCard({ item }: { item: any }) {
  const [isRead, setIsRead] = useState(item.isRead)
  const [isStarred, setIsStarred] = useState(item.isStarred)
  const [loading, setLoading] = useState(false)

  const handleRead = async () => {
    if (isRead) return
    setIsRead(true)
    try {
      await fetch(`/api/news/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isRead: true })
      })
    } catch (e) {
      console.error('Failed to mark as read', e)
    }
  }

  const toggleStar = async (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const newState = !isStarred
    setIsStarred(newState)

    try {
      await fetch(`/api/news/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isStarred: newState })
      })
    } catch (e) {
      console.error('Failed to toggle star', e)
      setIsStarred(!newState) // Revert on error
    }
  }

  return (
    <div className={cn(
      `group bg-slate-900/50 backdrop-blur-sm rounded-xl p-6 border transition-all duration-300 mb-4 hover:shadow-lg hover:shadow-black/20 relative`,
      isRead ? 'border-slate-800/60 bg-slate-950/30' : 'border-slate-800 bg-slate-900/50'
    )}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <CompetitorLogo
            name={item.competitor.name}
            website={item.competitor.website}
            className={cn("w-6 h-6 rounded-full flex-shrink-0 text-[9px] bg-slate-950 border-slate-800", isRead && "opacity-70")}
          />
          <span className={cn("text-sm font-semibold", isRead ? "text-slate-400" : "text-slate-200")}>
            {item.competitor.name}
          </span>
          <span className="text-slate-700">•</span>
          <span className="text-xs text-cyan-400/80 font-medium px-2 py-1 bg-cyan-950/20 border border-cyan-900/30 rounded-md">
            {item.eventType.replace(/_/g, ' ')}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleStar}
            className="text-slate-500 hover:text-yellow-400 transition-colors focus:outline-none"
          >
            <Star className={cn("w-4 h-4", isStarred ? "fill-yellow-400 text-yellow-400" : "")} />
          </button>

          <span className="text-xs text-slate-500 group-hover:text-slate-400 transition-colors">
            {format(new Date(item.date), 'MMMM d, yyyy')}
          </span>
        </div>
      </div>

      <h3 className={cn("text-lg font-medium mb-2 leading-tight transition-colors flex items-center gap-2", isRead ? "text-slate-400" : "text-slate-100 group-hover:text-cyan-400")}>
        <a
          href={item.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleRead}
          className="hover:underline decoration-cyan-500/30 underline-offset-4"
        >
          {item.title}
        </a>
      </h3>

      <p className={cn("text-sm leading-relaxed mb-4 max-w-3xl", isRead ? "text-slate-500" : "text-slate-400")}>
        {item.summary}
      </p>

      {/* Footer Meta */}
      {(item.details?.location || item.details?.products) && (
        <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-slate-800/50">
          {item.details.location && (
            <span className="inline-flex items-center text-xs text-slate-500">
              📍 {item.details.location}
            </span>
          )}
          {item.details.products?.map((prod: string) => (
            <span key={prod} className="inline-flex items-center text-xs text-slate-500 bg-slate-800/50 px-2 py-1 rounded border border-slate-800">
              {prod}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}