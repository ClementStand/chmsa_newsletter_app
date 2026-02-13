import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export async function GET() {
    try {
        const statusPath = path.join(process.cwd(), 'public', 'refresh_status.json')

        if (!fs.existsSync(statusPath)) {
            return NextResponse.json({
                status: 'idle',
                processed: 0,
                total: 0,
                percent_complete: 0,
                message: "No active refresh process found."
            })
        }

        const data = fs.readFileSync(statusPath, 'utf8')
        const json = JSON.parse(data)

        // Ensure we always return expected fields with defaults
        return NextResponse.json({
            status: json.status || 'idle',
            current_competitor: json.current_competitor,
            processed: json.processed || 0,
            total: json.total || 0,
            percent_complete: json.percent_complete || 0,
            estimated_seconds_remaining: json.estimated_seconds_remaining,
            started_at: json.started_at,
            completed_at: json.completed_at,
            error: json.error
        })
    } catch (error) {
        return NextResponse.json({
            status: 'error',
            error: 'Failed to read status',
            processed: 0,
            total: 0,
            percent_complete: 0
        }, { status: 500 })
    }
}
