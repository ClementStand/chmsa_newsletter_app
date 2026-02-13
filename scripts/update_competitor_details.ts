import fs from 'fs'
import path from 'path'
import { parse } from 'csv-parse/sync'
import { prisma } from '../src/lib/prisma'

async function main() {
    console.log('📊 Updating competitor details from CSV...')

    // Read CSV
    const csvPath = path.join(process.cwd(), 'competitors.csv')
    const fileContent = fs.readFileSync(csvPath, 'utf8')

    const records = parse(fileContent, {
        columns: true,
        skip_empty_lines: true
    }) as any[]

    let updated = 0
    let skipped = 0

    for (const record of records) {
        const name = record.Company?.trim()
        if (!name) continue
        if (name.toLowerCase().includes('abuzz')) continue

        const hq = record['HQ Location']?.trim() || null
        const employees = record['Approx Employees']?.trim() || null
        const revenue = record['Est. Revenue (USD)']?.trim() || null
        const funding = record['Funding/Status']?.trim() || null
        const markets = record['Key Markets']?.trim() || null

        // Only update existing competitors — don't create new ones
        try {
            const result = await prisma.competitor.updateMany({
                where: { name },
                data: {
                    headquarters: hq,
                    employeeCount: employees,
                    revenue: revenue,
                    fundingStatus: funding,
                    keyMarkets: markets,
                }
            })

            if (result.count > 0) {
                console.log(`  ✓ Updated: ${name}`)
                updated++
            } else {
                console.log(`  ⏭ Skipped (not in DB): ${name}`)
                skipped++
            }
        } catch (e: any) {
            console.log(`  ✗ Error updating ${name}: ${e.message}`)
        }
    }

    console.log(`\n✅ Done! Updated ${updated} competitors, skipped ${skipped}.`)
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
