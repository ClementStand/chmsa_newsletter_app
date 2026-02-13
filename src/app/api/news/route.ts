import { NextResponse } from 'next/server'
import { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'

export const dynamic = 'force-dynamic'

export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url)

        // Get filter params
        const competitorId = searchParams.get('competitor') || undefined
        const eventType = searchParams.get('eventType') || undefined
        const minThreat = searchParams.get('minThreat')
        const unreadOnly = searchParams.get('unread') === 'true'
        const starredOnly = searchParams.get('starred') === 'true'

        // Build where clause
        const where: Prisma.CompetitorNewsWhereInput = {
            AND: [
                {
                    sourceUrl: {
                        not: {
                            contains: 'example.com'
                        }
                    }
                }
            ]
        }

        if (competitorId) {
            where.competitorId = competitorId
        }

        if (eventType) {
            where.eventType = eventType
        }

        if (minThreat && !isNaN(parseInt(minThreat))) {
            where.threatLevel = {
                gte: parseInt(minThreat)
            }
        }

        if (unreadOnly) {
            where.isRead = false
        }

        if (starredOnly) {
            where.isStarred = true
        }

        const news = await prisma.competitorNews.findMany({
            where,
            include: {
                competitor: {
                    select: {
                        id: true,
                        name: true,
                        website: true
                    }
                }
            },
            orderBy: {
                date: 'desc'
            },
            take: 100
        })

        return NextResponse.json({ news })

    } catch (error) {
        console.error('Error fetching news:', error)
        return NextResponse.json(
            { error: 'Failed to fetch news' },
            { status: 500 }
        )
    }
}