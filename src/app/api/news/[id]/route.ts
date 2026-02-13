import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const newsItem = await prisma.competitorNews.findUnique({
            where: { id: params.id },
            include: { competitor: true }
        })

        if (!newsItem) {
            return NextResponse.json({ error: 'News item not found' }, { status: 404 })
        }

        return NextResponse.json(newsItem)
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch news item' }, { status: 500 })
    }
}

export async function PATCH(
    request: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const body = await request.json()
        const { isRead, isStarred } = body

        const updateData: any = {}
        if (isRead !== undefined) updateData.isRead = isRead
        if (isStarred !== undefined) updateData.isStarred = isStarred

        const updated = await prisma.competitorNews.update({
            where: { id: params.id },
            data: updateData
        })

        return NextResponse.json(updated)
    } catch (error) {
        return NextResponse.json({ error: 'Failed to update news item' }, { status: 500 })
    }
}
