
import { Badge } from "@/components/ui/badge"

const VARIANTS: Record<string, string> = {
    'New Project': 'bg-blue-600',
    'Investment': 'bg-green-600',
    'Award': 'bg-yellow-600',
    'Product Launch': 'bg-purple-600',
    'Partnership': 'bg-indigo-600',
    'Leadership Change': 'bg-pink-600',
    'Market Expansion': 'bg-teal-600',
    'Technical Innovation': 'bg-cyan-600',
}

export function EventTypeBadge({ type }: { type: string }) {
    const color = VARIANTS[type] || 'bg-slate-600'

    return (
        <Badge className={`${color} text-white border-none hover:${color}`}>
            {type}
        </Badge>
    )
}
