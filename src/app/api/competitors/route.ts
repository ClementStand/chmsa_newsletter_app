import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'

export async function GET() {
    try {
        const competitors = await prisma.competitor.findMany({
            include: {
                _count: {
                    select: { news: true }
                }
            },
            orderBy: { name: 'asc' }
        })

        const formatted = competitors.map(c => ({
            ...c,
            newsCount: c._count.news
        }))

        return NextResponse.json(formatted)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to fetch competitors' }, { status: 500 })
    }
}

export async function POST(request: Request) {
    try {
        const { name, website, region } = await request.json()

        const competitor = await prisma.competitor.create({
            data: {
                name,
                website,
                region,
                status: 'active'
            }
        })
        return NextResponse.json(competitor)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to create competitor' }, { status: 500 })
    }
}

export async function PATCH(request: Request) {
    try {
        const { id, status } = await request.json()
        const competitor = await prisma.competitor.update({
            where: { id },
            data: { status }
        })
        return NextResponse.json(competitor)
    } catch (error) {
        console.error(error)
        return NextResponse.json({ error: 'Failed to update competitor' }, { status: 500 })
    }
}
