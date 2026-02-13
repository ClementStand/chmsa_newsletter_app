
const { PrismaClient } = require('@prisma/client')
const prisma = new PrismaClient()

async function main() {
    const allNews = await prisma.competitorNews.findMany({
        select: { extractedAt: true }
    })

    console.log(`Total items: ${allNews.length}`)

    if (allNews.length === 0) return

    const dates = allNews.map(n => new Date(n.extractedAt).getTime())
    const min = new Date(Math.min(...dates))
    const max = new Date(Math.max(...dates))

    console.log(`Earliest extractedAt: ${min.toISOString()}`)
    console.log(`Latest extractedAt:   ${max.toISOString()}`)

    // Count items in last 7 days
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
    const recentCount = allNews.filter(n => new Date(n.extractedAt) >= sevenDaysAgo).length
    console.log(`Items in last 7 days: ${recentCount}`)
}

main()
    .catch(e => console.error(e))
    .finally(async () => await prisma.$disconnect())
