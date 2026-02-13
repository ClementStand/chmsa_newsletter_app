'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { Sidebar } from '@/components/Sidebar'
import { CompetitorLogo } from "@/components/ui/CompetitorLogo"
import { Plus, Archive, RefreshCw, X } from 'lucide-react'

export default function CompetitorsPage() {
    const [competitors, setCompetitors] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [isAdding, setIsAdding] = useState(false)

    // New Competitor State
    const [newName, setNewName] = useState('')
    const [newWebsite, setNewWebsite] = useState('')
    const [newRegion, setNewRegion] = useState('Global')

    const fetchCompetitors = async () => {
        try {
            const res = await fetch('/api/competitors')
            const data = await res.json()
            setCompetitors(data)
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchCompetitors()
    }, [])

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            await fetch('/api/competitors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newName,
                    website: newWebsite,
                    region: newRegion
                })
            })
            setNewName('')
            setNewWebsite('')
            setIsAdding(false)
            fetchCompetitors()
        } catch (error) {
            console.error(error)
        }
    }

    const handleStatusChange = async (id: string, newStatus: string) => {
        try {
            await fetch('/api/competitors', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, status: newStatus })
            })
            // Optimistic update
            setCompetitors(prev => prev.map(c => c.id === id ? { ...c, status: newStatus } : c))
        } catch (error) {
            console.error(error)
        }
    }

    const activeCompetitors = competitors.filter(c => c.status !== 'archived')
    const archivedCompetitors = competitors.filter(c => c.status === 'archived')

    return (
        <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans">
            <Suspense fallback={<div className="w-64 bg-slate-950 border-r border-slate-800 h-screen" />}>
                <Sidebar />
            </Suspense>

            <main className="flex-1 ml-64 p-12">
                <div className="max-w-4xl mx-auto">
                    <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-6">
                        <div>
                            <h1 className="text-3xl font-bold text-white mb-2">Manage Competitors</h1>
                            <p className="text-slate-400">Add unwanted competitors to archive to hide their data.</p>
                        </div>
                        <button
                            onClick={() => setIsAdding(!isAdding)}
                            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-md flex items-center gap-2 transition-colors"
                        >
                            <Plus className="w-4 h-4" /> Add Competitor
                        </button>
                    </div>

                    {/* Add Form */}
                    {isAdding && (
                        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8 animate-in slide-in-from-top-4 fade-in">
                            <h2 className="text-lg font-semibold text-white mb-4">Add New Competitor</h2>
                            <form onSubmit={handleAdd} className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm text-slate-400 mb-1">Company Name</label>
                                        <input
                                            type="text"
                                            required
                                            value={newName}
                                            onChange={e => setNewName(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                                            placeholder="e.g. Acme Corp"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-slate-400 mb-1">Website URL</label>
                                        <input
                                            type="url"
                                            value={newWebsite}
                                            onChange={e => setNewWebsite(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                                            placeholder="e.g. https://example.com"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-slate-400 mb-1">Region</label>
                                        <select
                                            value={newRegion}
                                            onChange={e => setNewRegion(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                                        >
                                            <option value="Global">Global</option>
                                            <option value="MENA">MENA</option>
                                            <option value="Europe">Europe</option>
                                            <option value="North America">North America</option>
                                            <option value="APAC">APAC</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="flex gap-2 justify-end pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setIsAdding(false)}
                                        className="px-4 py-2 text-slate-400 hover:text-white"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded font-medium"
                                    >
                                        Save Competitor
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    {/* Active List */}
                    <div className="space-y-6">
                        <div>
                            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                                Active Competitors ({activeCompetitors.length})
                            </h2>
                            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-800">
                                {activeCompetitors.map(comp => (
                                    <div key={comp.id} className="relative">
                                        <Link
                                            href={`/competitor/${comp.id}`}
                                            className="p-4 flex items-center justify-between group hover:bg-slate-800/50 transition-colors block"
                                        >
                                            <div className="flex items-center gap-4">
                                                <CompetitorLogo
                                                    name={comp.name}
                                                    website={comp.website}
                                                    className="w-10 h-10 rounded-lg"
                                                />
                                                <div>
                                                    <h3 className="font-medium text-white group-hover:text-cyan-400 transition-colors">{comp.name}</h3>
                                                    <div className="flex items-center gap-2 text-sm text-slate-500">
                                                        <span>{comp.region || 'Global'}</span>
                                                        <span>•</span>
                                                        <a
                                                            href={comp.website}
                                                            target="_blank"
                                                            onClick={(e) => e.stopPropagation()}
                                                            className="hover:text-cyan-400 transition-colors truncate max-w-[200px]"
                                                        >
                                                            {comp.website}
                                                        </a>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="text-center px-4">
                                                    <div className="text-lg font-bold text-slate-300">{comp.newsCount}</div>
                                                    <div className="text-[10px] text-slate-500 uppercase">Signals</div>
                                                </div>
                                            </div>
                                        </Link>

                                        {/* Archive button - positioned absolutely to avoid click conflicts */}
                                        <button
                                            onClick={(e) => {
                                                e.preventDefault()
                                                e.stopPropagation()
                                                handleStatusChange(comp.id, 'archived')
                                            }}
                                            className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors z-10"
                                            title="Archive Competitor"
                                        >
                                            <Archive className="w-5 h-5" />
                                        </button>
                                    </div>
                                ))}
                                {activeCompetitors.length === 0 && (
                                    <div className="p-8 text-center text-slate-500">No active competitors found.</div>
                                )}
                            </div>
                        </div>

                        {/* Archived List */}
                        {archivedCompetitors.length > 0 && (
                            <div className="opacity-70 hover:opacity-100 transition-opacity">
                                <h2 className="text-lg font-semibold text-slate-400 mb-4 flex items-center gap-2">
                                    <Archive className="w-5 h-5" />
                                    Archived ({archivedCompetitors.length})
                                </h2>
                                <div className="bg-slate-950/30 border border-slate-800/50 rounded-xl overflow-hidden divide-y divide-slate-800/50">
                                    {archivedCompetitors.map(comp => (
                                        <div key={comp.id} className="p-3 flex items-center justify-between">
                                            <div className="flex items-center gap-3 grayscale">
                                                <CompetitorLogo
                                                    name={comp.name}
                                                    website={comp.website}
                                                    className="w-8 h-8 rounded-lg"
                                                />
                                                <span className="text-slate-400">{comp.name}</span>
                                            </div>
                                            <button
                                                onClick={() => handleStatusChange(comp.id, 'active')}
                                                className="px-3 py-1 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 flex items-center gap-2"
                                            >
                                                <RefreshCw className="w-3 h-3" /> Restore
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                </div>
            </main>
        </div>
    )
}
