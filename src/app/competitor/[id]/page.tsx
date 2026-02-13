import Link from 'next/link'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Globe, Brain, UserCheck, Activity, Calendar, MapPin, Users, DollarSign, TrendingUp } from "lucide-react"
import { format } from 'date-fns'
import NewsCard from "@/components/ui/NewsCard"
import { prisma } from '@/lib/prisma'

async function getCompetitor(id: string) {
    return await prisma.competitor.findUnique({
        where: { id },
        include: {
            news: {
                orderBy: { date: 'desc' },
                include: { competitor: true }
            }
        }
    })
}

export default async function CompetitorPage({ params }: { params: { id: string } }) {
    const competitor = await getCompetitor(params.id)

    if (!competitor) {
        return <div className="min-h-screen bg-slate-950 text-slate-400 flex items-center justify-center">Competitor not found</div>
    }

    // 1. Extract Tech Stack from News Details
    const techStack = new Set<string>()
    competitor.news.forEach(item => {
        try {
            if (item.details) {
                const details = JSON.parse(item.details as string)
                if (details.products && Array.isArray(details.products)) {
                    details.products.forEach((p: string) => techStack.add(p))
                }
            }
        } catch (e) { }
    })

    // 2. Extract Leadership Changes
    const leadershipNews = competitor.news.filter(n =>
        n.eventType === 'Leadership Change' ||
        n.title.toLowerCase().includes('ceo') ||
        n.title.toLowerCase().includes('appoint')
    )

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 pb-20 font-sans">
            <div className="container mx-auto px-6 py-8 max-w-5xl">
                {/* Back Link */}
                <Link
                    href="/"
                    className="inline-flex items-center text-slate-500 hover:text-cyan-400 transition-colors mb-8 group"
                >
                    <ArrowLeft className="mr-2 h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                    Back to Dashboard
                </Link>

                {/* Header Profile */}
                <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 mb-8 relative overflow-hidden group hover:border-slate-700 transition-all">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>

                    <div className="flex flex-col md:flex-row justify-between items-start gap-6 relative z-10">
                        <div>
                            <div className="flex items-center gap-4 mb-4">
                                <h1 className="text-4xl font-bold text-white tracking-tight">{competitor.name}</h1>
                                {competitor.status === 'Active' && (
                                    <span className="relative flex h-3 w-3">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                                    </span>
                                )}
                            </div>

                            <div className="flex flex-wrap gap-2 mb-4">
                                {competitor.industry && (
                                    <Badge variant="outline" className="bg-slate-950/50 border-slate-700 text-slate-300">
                                        {competitor.industry}
                                    </Badge>
                                )}
                                {competitor.region && (
                                    <Badge variant="outline" className="bg-slate-950/50 border-slate-700 text-slate-300">
                                        📍 {competitor.region}
                                    </Badge>
                                )}
                            </div>

                            {competitor.description && (
                                <p className="text-slate-400 max-w-2xl leading-relaxed text-lg">
                                    {competitor.description}
                                </p>
                            )}
                        </div>

                        {competitor.website && (
                            <a href={competitor.website} target="_blank" rel="noreferrer">
                                <Button className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 gap-2 shadow-lg shadow-black/20">
                                    <Globe className="h-4 w-4 text-cyan-400" />
                                    Visit Website
                                </Button>
                            </a>
                        )}
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Left Column: Stats & Info */}
                    <div className="space-y-6">
                        {/* Company Overview Widget */}
                        {(competitor.headquarters || competitor.employeeCount || competitor.revenue || competitor.keyMarkets || competitor.fundingStatus) && (
                            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                    <Activity className="w-4 h-4 text-cyan-400" />
                                    Company Overview
                                </h3>
                                <div className="space-y-3">
                                    {competitor.headquarters && (
                                        <div className="flex items-start gap-3">
                                            <MapPin className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                                            <div>
                                                <div className="text-[10px] text-slate-500 uppercase tracking-wider">Headquarters</div>
                                                <div className="text-sm text-slate-200 font-medium">{competitor.headquarters}</div>
                                            </div>
                                        </div>
                                    )}
                                    {competitor.employeeCount && (
                                        <div className="flex items-start gap-3">
                                            <Users className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                                            <div>
                                                <div className="text-[10px] text-slate-500 uppercase tracking-wider">Employees</div>
                                                <div className="text-sm text-slate-200 font-medium">{competitor.employeeCount}</div>
                                            </div>
                                        </div>
                                    )}
                                    {competitor.revenue && (
                                        <div className="flex items-start gap-3">
                                            <DollarSign className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                                            <div>
                                                <div className="text-[10px] text-slate-500 uppercase tracking-wider">Est. Revenue</div>
                                                <div className="text-sm text-slate-200 font-medium">{competitor.revenue}</div>
                                            </div>
                                        </div>
                                    )}
                                    {competitor.keyMarkets && (
                                        <div className="flex items-start gap-3">
                                            <Globe className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                                            <div>
                                                <div className="text-[10px] text-slate-500 uppercase tracking-wider">Key Markets</div>
                                                <div className="text-sm text-slate-200 font-medium">{competitor.keyMarkets}</div>
                                            </div>
                                        </div>
                                    )}
                                    {competitor.fundingStatus && (
                                        <div className="flex items-start gap-3">
                                            <TrendingUp className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                                            <div>
                                                <div className="text-[10px] text-slate-500 uppercase tracking-wider">Funding / Status</div>
                                                <div className="text-sm text-slate-200 font-medium">{competitor.fundingStatus}</div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Tech Stack Widget */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <Brain className="w-4 h-4 text-cyan-400" />
                                Detect Tech Stack
                            </h3>
                            {techStack.size > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {Array.from(techStack).map(tech => (
                                        <Badge key={tech} className="bg-cyan-950/30 text-cyan-300 border-cyan-900/50 hover:bg-cyan-900/50 transition-colors">
                                            {tech}
                                        </Badge>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-slate-600 text-sm italic">No technology signals detected yet.</p>
                            )}
                        </div>

                        {/* Leadership Widget */}
                        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <UserCheck className="w-4 h-4 text-purple-400" />
                                Leadership Recent
                            </h3>
                            {leadershipNews.length > 0 ? (
                                <div className="space-y-4">
                                    {leadershipNews.slice(0, 3).map(item => (
                                        <div key={item.id} className="border-l-2 border-slate-800 pl-3 py-1">
                                            <div className="text-xs text-slate-500 mb-1">{format(new Date(item.date), 'MMM yyyy')}</div>
                                            <div className="text-sm text-slate-200 font-medium leading-tight hover:text-cyan-400 transition-colors">
                                                <a href={item.sourceUrl} target="_blank">{item.title}</a>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-slate-600 text-sm italic">No recent leadership changes.</p>
                            )}
                        </div>
                    </div>

                    {/* Right Column: Timeline */}
                    <div className="md:col-span-2">
                        <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-cyan-400" />
                            Intelligence Timeline
                        </h2>

                        <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-800 before:to-transparent">
                            {competitor.news.length === 0 ? (
                                <div className="text-center py-10 bg-slate-900/30 rounded-xl border border-dashed border-slate-800">
                                    <p className="text-slate-500 italic">No intelligence data found.</p>
                                </div>
                            ) : (
                                competitor.news.map((item, idx) => (
                                    <div key={item.id} className="relative pl-12">
                                        {/* Timeline Dot */}
                                        <div className="absolute left-2 top-8 w-6 h-6 bg-slate-950 border-2 border-slate-700 rounded-full flex items-center justify-center z-10 group-hover:border-cyan-500 transition-colors">
                                            <div className={`w-2 h-2 rounded-full ${idx === 0 ? 'bg-cyan-400 animate-pulse' : 'bg-slate-600'}`}></div>
                                        </div>

                                        {/* Date Label */}
                                        <div className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-2">
                                            {format(new Date(item.date), 'MMM d')}
                                        </div>

                                        <NewsCard item={item} />
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
