'use client'
import { useState, useEffect, Suspense } from 'react'
import { format, subDays } from 'date-fns'
import { Sidebar } from '@/components/Sidebar'
import { Star, ExternalLink, FileText } from 'lucide-react'

export default function WeeklyDebrief() {
    const [debrief, setDebrief] = useState<string | null>(null)
    const [loading, setLoading] = useState(true)
    const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(null)
    const [periodStart, setPeriodStart] = useState<Date | null>(null)
    const [periodEnd, setPeriodEnd] = useState<Date | null>(null)
    const [topArticles, setTopArticles] = useState<any[]>([])

    useEffect(() => {
        const fetchData = async () => {
            try {
                const startDate = subDays(new Date(), 7).toISOString()
                const endDate = new Date().toISOString()

                const [debriefRes, articlesRes] = await Promise.all([
                    fetch('/api/debrief', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: 'latest' })
                    }),
                    fetch('/api/debrief', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: 'top_articles', startDate, endDate })
                    })
                ])

                const debriefData = await debriefRes.json()
                if (debriefData.response) {
                    setDebrief(debriefData.response)
                    setLastGeneratedAt(debriefData.generatedAt)
                    setPeriodStart(new Date(debriefData.periodStart))
                    setPeriodEnd(new Date(debriefData.periodEnd))
                }

                const articlesData = await articlesRes.json()
                setTopArticles(articlesData.topArticles || [])
            } catch (e) {
                console.error('Failed to load debrief:', e)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    const handlePrint = () => window.print()

    const displayStart = periodStart || subDays(new Date(), 7)
    const displayEnd = periodEnd || new Date()

    // Extract the Executive Summary from the debrief markdown
    const getShortSummary = (md: string): string[] => {
        const lines = md.split('\n')
        let inSummary = false
        const bullets: string[] = []
        for (const line of lines) {
            // Look for the EXECUTIVE SUMMARY heading
            if (line.toLowerCase().includes('executive summary')) {
                inSummary = true
                continue
            }
            // Stop at the next major heading
            if (inSummary && line.startsWith('## ')) break
            // Collect content lines
            if (inSummary && line.trim() && !line.startsWith('---')) {
                const clean = line.trim()
                    .replace(/\*\*/g, '')
                    .replace(/\*/g, '')
                    .replace(/^[-•]\s*/, '')
                    .replace(/^>\s*/, '')
                if (clean.length > 10) {
                    bullets.push(clean)
                }
                if (bullets.length >= 5) break
            }
        }
        return bullets
    }

    return (
        <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
            <div className="print:hidden">
                <Suspense fallback={<div className="w-64 bg-slate-950 border-r border-slate-800 h-screen" />}>
                    <Sidebar />
                </Suspense>
            </div>

            <main className="flex-1 ml-64 p-8 md:p-12 print:ml-0 print:p-0">
                <div className="max-w-3xl mx-auto">
                    {/* Header */}
                    <div className="flex items-end justify-between mb-10 border-b border-slate-800 pb-5">
                        <div>
                            <h1 className="text-2xl font-bold text-white mb-1">Weekly Debrief</h1>
                            <p className="text-slate-500 text-sm">
                                {`${format(displayStart, 'MMM d')} — ${format(displayEnd, 'MMM d, yyyy')}`}
                            </p>
                        </div>
                        <button
                            onClick={handlePrint}
                            disabled={!debrief && topArticles.length === 0}
                            className="print:hidden px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md text-sm transition-colors disabled:opacity-50"
                        >
                            Print / PDF
                        </button>
                    </div>

                    {/* Loading */}
                    {loading && (
                        <div className="py-20 text-center animate-pulse">
                            <div className="w-12 h-12 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto mb-4"></div>
                            <p className="text-slate-400">Loading debrief...</p>
                        </div>
                    )}

                    {!loading && (
                        <>
                            {/* ============ TOP 3 ARTICLES ============ */}
                            {topArticles.length > 0 && (
                                <section className="mb-10">
                                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <Star className="w-4 h-4 text-amber-400" />
                                        Top Articles This Week
                                    </h2>
                                    <div className="space-y-3">
                                        {topArticles.map((article: any, idx: number) => (
                                            <a
                                                key={article.id}
                                                href={article.sourceUrl}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="block bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 hover:bg-slate-900/80 transition-all group"
                                            >
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1 min-w-0">
                                                        <h3 className="text-base font-semibold text-white group-hover:text-cyan-300 transition-colors leading-snug mb-1">
                                                            {article.title}
                                                        </h3>
                                                        <p className="text-sm text-slate-400 line-clamp-2">{article.summary}</p>
                                                        <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
                                                            <span>{article.competitor?.name}</span>
                                                            <span>·</span>
                                                            <span>{format(new Date(article.date), 'MMM d, yyyy')}</span>
                                                        </div>
                                                    </div>
                                                    <ExternalLink className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition-colors shrink-0 mt-1" />
                                                </div>
                                            </a>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {/* ============ SUMMARY ============ */}
                            {debrief && (
                                <section className="mb-10">
                                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                        <FileText className="w-4 h-4 text-cyan-400" />
                                        Summary
                                    </h2>
                                    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
                                        <ul className="space-y-2">
                                            {getShortSummary(debrief).map((point, i) => (
                                                <li key={i} className="flex items-start gap-3 text-sm text-slate-300 leading-relaxed">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-2 shrink-0" />
                                                    {point}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    {lastGeneratedAt && (
                                        <p className="text-[10px] text-slate-600 mt-2">
                                            Generated {format(new Date(lastGeneratedAt), 'MMM d, yyyy \'at\' h:mm a')}
                                        </p>
                                    )}
                                </section>
                            )}

                            {/* Empty State */}
                            {!debrief && topArticles.length === 0 && (
                                <div className="py-20 text-center border-2 border-dashed border-slate-800 rounded-xl bg-slate-900/50">
                                    <p className="text-slate-500">
                                        No debrief generated yet. Run the generator script locally:
                                    </p>
                                    <code className="block mt-4 text-cyan-400 text-sm bg-slate-900 px-4 py-2 rounded-lg inline-block">
                                        ./.venv/bin/python scripts/debrief_generator.py
                                    </code>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
