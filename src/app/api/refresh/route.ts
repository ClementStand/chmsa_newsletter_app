import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'
import { NextResponse } from 'next/server'

// Prevent Vercel/Next from killing the process (works best locally)
export const dynamic = 'force-dynamic'

export async function POST() {
    try {
        const scriptPath = path.join(process.cwd(), 'scripts', 'news_fetcher.py')
        const pythonCommand = './.venv/bin/python'
        const logPath = path.join(process.cwd(), 'public', 'refresh_log.txt')

        console.log('Spawning background news fetcher...')
        console.log('Script path:', scriptPath)
        console.log('Python command:', pythonCommand)

        // Open log file for writing
        const logFile = fs.openSync(logPath, 'w')

        const child = spawn(pythonCommand, [scriptPath], {
            detached: true,
            stdio: ['ignore', logFile, logFile], // Redirect stdout/stderr to log file
            cwd: process.cwd(),
            env: { ...process.env } // Pass all environment variables
        })

        child.on('error', (err) => {
            console.error('Failed to start subprocess:', err)
            fs.writeFileSync(logPath, `Spawn error: ${err.message}\n`)
        })

        child.unref()

        return NextResponse.json({ success: true, message: "Refresh started in background" })
    } catch (error: any) {
        console.error(`Spawn error: ${error}`)
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}
