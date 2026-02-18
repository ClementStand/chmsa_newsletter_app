import { prisma } from '../lib/prisma'
import { Sidebar } from '../components/Sidebar'
import NewsFeed from '../components/NewsFeed'
import ThreatFilter from '../components/ThreatFilter'
import { RightSidebar } from '../components/RightSidebar'
import SurveillanceMap from '../components/SurveillanceMap'

import { subHours, subDays } from 'date-fns'

export default async function Home({
  searchParams,
}: {
  searchParams: { competitorId?: string; minThreat?: string; unread?: string; starred?: string; region?: string; location?: string }
}) {
  /* const minThreat = searchParams.minThreat ? parseInt(searchParams.minThreat) : 1 */
  const where: any = {}

  if (searchParams.competitorId) {
    where.competitorId = searchParams.competitorId
  }

  if (searchParams.unread === 'true') {
    where.isRead = false
  }

  if (searchParams.starred === 'true') {
    where.isStarred = true
  }

  if (searchParams.region) {
    let regionVal = searchParams.region
    if (regionVal === 'Middle East') regionVal = 'MENA'

    // Smart region matching: map broad region names to possible DB values
    const regionMappings: { [key: string]: string[] } = {
      'North America': ['north america', 'us', 'usa', 'canada', 'america'],
      'Europe': ['europe', 'uk', 'germany', 'france', 'spain', 'italy', 'netherlands', 'sweden', 'denmark', 'ireland', 'switzerland', 'belgium', 'austria', 'poland', 'norway', 'finland'],
      'MENA': ['mena', 'middle east', 'uae', 'saudi', 'qatar', 'dubai', 'abu dhabi', 'israel', 'turkey', 'egypt'],
      'APAC': ['apac', 'asia', 'china', 'japan', 'korea', 'india', 'singapore', 'australia', 'pacific'],
      'Global': ['global'],
    }

    const keywords = regionMappings[regionVal]
    if (keywords) {
      where.OR = keywords.map(k => ({
        region: { contains: k, mode: 'insensitive' }
      }))
    } else {
      where.region = { equals: regionVal, mode: 'insensitive' }
    }
  }

  if (searchParams.location) {
    // Case-insensitive fuzzy search within the JSON string
    where.details = {
      contains: searchParams.location,
      mode: 'insensitive'
    }
  }

  // 3. Fetch Data
  const news = await prisma.competitorNews.findMany({
    where,
    orderBy: { date: 'desc' },
    include: { competitor: true },
  })

  // Calculate Stats
  const now = new Date()
  const last24h = subHours(now, 24)

  const stats = {
    total: news.length,
    highThreat: news.filter((n: any) => n.threatLevel >= 4).length,
    unread: news.filter((n: any) => !n.isRead).length,
    last24h: news.filter((n: any) => new Date(n.date) > last24h).length
  }

  // Calculate Top Movers (Last 7 Days)
  const last7Days = subDays(now, 7)

  const recentNews = news.filter((n: any) => new Date(n.date) >= last7Days)
  const competitorCounts: Record<string, number> = {}

  recentNews.forEach((n: any) => {
    const name = n.competitor.name
    competitorCounts[name] = (competitorCounts[name] || 0) + 1
  })

  // Sort and take top 5
  const topMovers = Object.entries(competitorCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)

  return (
    <div className="flex min-h-screen bg-background text-foreground font-sans selection:bg-cyan-900 selection:text-cyan-100">
      <Sidebar />

      <main className="flex-1 ml-64 p-8">
        <div className="flex items-start gap-8 max-w-[1600px] mx-auto">

          {/* Main Feed Column */}
          <div className="flex-1 min-w-0">
            {/* Map Section */}
            <SurveillanceMap news={news} />

            <div className="flex justify-between items-start gap-6 mb-8 bg-slate-950/50 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm shadow-sm relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-950/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              <div className="relative z-10 flex-1">
                <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                  Market Intelligence
                </h1>
                <p className="text-muted-foreground text-sm mt-1">
                  Real-time surveillance feed • {news.length} updates found
                </p>
              </div>

              {/* Refresh Button - Removed as per request */}
              {/* <div className="relative z-10 w-64">
                  <DashboardRefreshButton />
                </div> */}
            </div>

            {/* ✅ Passing the server-fetched news to the component */}
            <NewsFeed initialNews={news} />
          </div>

          {/* Right Sidebar Column */}
          <RightSidebar stats={stats} topMovers={topMovers} latestIntercepts={news.slice(0, 3)} />

        </div>
      </main>
    </div>
  )
}