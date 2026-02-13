import { TrendingUp, ShieldAlert, Clock, Radio } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface RightSidebarProps {
    stats: {
        total: number
        highThreat: number
        unread: number
        last24h: number
    }
    topMovers?: { name: string, count: number }[]
    latestIntercepts?: any[]
}

export function RightSidebar({ stats, topMovers = [], latestIntercepts = [] }: RightSidebarProps) {
    // Helper for Activity Level
    const getActivityLevel = (count: number) => {
        if (count >= 5) return <span className="text-emerald-400 font-bold text-[10px] bg-emerald-400/10 px-2 py-0.5 rounded ml-2 uppercase tracking-wide">High Activity 📈</span>
        if (count >= 3) return <span className="text-cyan-400 font-bold text-[10px] bg-cyan-400/10 px-2 py-0.5 rounded ml-2 uppercase tracking-wide">Medium Activity</span>
        return <span className="text-slate-500 font-bold text-[10px] bg-slate-800 px-2 py-0.5 rounded ml-2 uppercase tracking-wide">Low Activity</span>
    }

    return (
        <div className="w-80 hidden xl:block sticky top-6 space-y-6">

            {/* Top Movers Leaderboard */}
            <div className="p-4 rounded-xl bg-slate-950/50 backdrop-blur-sm border border-slate-800 shadow-lg">
                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2 border-b border-slate-800 pb-3">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    Top Movers (7 Days)
                </h3>

                <div className="space-y-3">
                    {topMovers.length > 0 ? (
                        topMovers.map((mover, i) => (
                            <div key={i} className="flex flex-col border-b border-slate-800/50 last:border-0 pb-2 last:pb-0">
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-slate-200 font-medium text-sm">{mover.name}</span>
                                    <span className="text-xs text-slate-500 font-mono">{mover.count} Upds</span>
                                </div>
                                <div>
                                    {getActivityLevel(mover.count)}
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-center py-4 text-slate-500 text-xs italic">
                            No significant movement detected.
                        </div>
                    )}
                </div>
            </div>

            {/* Live Intercepts Radar */}
            <div className="p-4 rounded-xl bg-slate-950/50 backdrop-blur-sm border border-slate-800 shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 p-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]"></div>
                </div>

                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2 border-b border-slate-800 pb-3">
                    <Radio className="w-4 h-4 text-red-500" />
                    Live Intercepts
                </h3>

                <div className="space-y-4">
                    {latestIntercepts.map((item, i) => (
                        <div key={i} className="text-sm">
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-cyan-500 font-mono text-xs font-bold whitespace-nowrap">
                                    {formatDistanceToNow(new Date(item.date), { addSuffix: true }).replace('about ', '')}
                                </span>
                                <span className="text-slate-200 font-medium truncate">{item.competitor.name}</span>
                            </div>
                            <p className="text-slate-500 text-xs line-clamp-2 leading-relaxed pl-2 border-l-2 border-slate-800">
                                {item.title}
                            </p>
                        </div>
                    ))}
                    {latestIntercepts.length === 0 && (
                        <div className="text-center py-4 text-slate-500 text-xs italic">
                            Scanning for signals...
                        </div>
                    )}
                </div>
            </div>

            {/* Disclaimer */}
            <div className="text-xs text-slate-600 text-center px-4">
                <p>Abuzz Solutions Intel Platform v1.0</p>
                <p className="mt-1">Confidential & Proprietary</p>
            </div>
        </div>
    )
}
