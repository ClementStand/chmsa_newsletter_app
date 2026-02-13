
import * as React from "react"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { RefreshCw } from "lucide-react"

export function RefreshButton() {
    const router = useRouter()
    const [loading, setLoading] = React.useState(false)

    const handleRefresh = async () => {
        setLoading(true)
        try {
            await fetch('/api/refresh', { method: 'POST' })
            router.refresh()
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Button
            variant="default"
            size="lg"
            onClick={handleRefresh}
            disabled={loading}
            className="w-full gap-3 bg-cyan-500 hover:bg-cyan-400 text-white shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] transition-all duration-300 font-bold tracking-wider group relative overflow-hidden"
        >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-shimmer" />
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'SCANNING NETWORKS...' : 'SCAN FOR NEW INTEL'}
        </Button>
    )
}
