
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    console.log('🧹 Purging CompetitorNews table...')
    try {
        const { count } = await prisma.competitorNews.deleteMany({})
        console.log(`✅ Deleted ${count} records.`)
    } catch (e) {
        console.error('❌ Error purging table:', e)
    } finally {
        await prisma.$disconnect()
    }
}

main()
