
const { PrismaClient } = require('@prisma/client')

const prisma = new PrismaClient()

async function main() {
    const comps = await prisma.competitor.findMany({
        select: { name: true, website: true }
    })

    console.log("Checking Competitor Websites:")
    comps.forEach((c: any) => {
        console.log(`${c.name}: '${c.website}'`)
    })
}

main()
    .catch(e => console.error(e))
    .finally(async () => await prisma.$disconnect())
