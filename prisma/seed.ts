import { prisma } from '../src/lib/prisma'

const COMPETITORS = [
    {
        name: 'Indústrias Romi',
        website: 'https://www.romi.com',
        region: 'Brasil',
        headquarters: 'Santa Bárbara d\'Oeste, SP',
        description: 'Leading manufacturer of machine tools, plastic processing machines, and cast iron parts.',
        industry: 'Industrial Machinery',
        status: 'active',
        employeeCount: '2,800+',     //
        revenue: '$240M USD',        // Converted from 1.39bn BRL
        keyMarkets: 'Brazil, Germany, USA, UK, Mexico',
        fundingStatus: 'Public (BVMF: ROMI3)'
    },
    {
        name: 'Fagor Automation',
        website: 'https://www.fagorautomation.com',
        region: 'Global / Spain',
        headquarters: 'Mondragón, Spain',
        description: 'Development and manufacturing of automation and control systems (CNC) for industrial machinery.',
        industry: 'Automation & Control',
        status: 'active',
        employeeCount: '650+',       // Automation division specific
        revenue: '$168M USD',        // Estimated annual revenue
        keyMarkets: 'Global (50+ offices worldwide)',
        fundingStatus: 'Cooperative (Mondragon Corp)'
    },
    {
        name: 'Eurostec',
        website: 'https://www.eurostec.com.br',
        region: 'Brasil',
        headquarters: 'Caxias do Sul, RS',
        description: 'Major distributor of high-tech industrial machinery and solutions in Brazil.',
        industry: 'Machinery Supply',
        status: 'active',
        employeeCount: '50-200',     // Estimated for large regional distributor
        revenue: 'Private',
        keyMarkets: 'Brasil (South/Southeast)',
        fundingStatus: 'Private'
    },
    {
        name: 'Alletech Máquinas',
        website: 'https://alletech.com.br',
        region: 'Brasil',
        headquarters: 'Pomerode, SC',
        description: 'Specialized machinery dealer focused on CNC solutions and technical support.',
        industry: 'Industrial Equipment',
        status: 'active',
        employeeCount: '10-50',      // Estimated for specialized dealer
        revenue: 'Private',
        keyMarkets: 'Brasil (Santa Catarina)',
        fundingStatus: 'Private'
    }
]

async function main() {
    console.log('🌱 Seeding CIMHSA competitors...')

    // 1. Clear existing data to avoid duplicates
    try {
        await prisma.competitorNews.deleteMany({})
        await prisma.competitor.deleteMany({})
        console.log('🧹 Cleared old data.')
    } catch (e) {
        console.log('⚠️  Could not clear old data (maybe tables are empty), continuing...')
    }

    // 2. Insert the 4 Competitors
    for (const company of COMPETITORS) {
        await prisma.competitor.create({
            data: {
                name: company.name,
                website: company.website,
                region: company.region,
                headquarters: company.headquarters,
                description: company.description,
                industry: company.industry,
                status: company.status,
                employeeCount: company.employeeCount,
                revenue: company.revenue,
                keyMarkets: company.keyMarkets,
                fundingStatus: company.fundingStatus
            }
        })
        console.log(`  ✓ Created ${company.name}`)
    }

    const count = await prisma.competitor.count()
    console.log(`\n✅ Seeding complete! ${count} competitors loaded.`)
}

main()
    .then(async () => {
        await prisma.$disconnect()
    })
    .catch(async (e) => {
        console.error(e)
        await prisma.$disconnect()
        process.exit(1)
    })