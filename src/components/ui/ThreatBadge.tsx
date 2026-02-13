
import { Badge } from "@/components/ui/badge"

const COLORS = {
    1: 'bg-gray-500 text-white',
    2: 'bg-emerald-500 text-white',
    3: 'bg-amber-500 text-white',
    4: 'bg-orange-500 text-white',
    5: 'bg-red-600 text-white',
}

export function ThreatBadge({ level }: { level: number }) {
    const color = COLORS[level as keyof typeof COLORS] || COLORS[1]

    return (
        <Badge className={`${color} px-2 py-0.5 border-none`}>
            Level {level}
        </Badge>
    )
}
