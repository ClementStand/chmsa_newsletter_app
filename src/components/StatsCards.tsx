
import { Card, CardContent } from "@/components/ui/card"
import { TrendingUp, Bell, AlertTriangle, Calendar } from "lucide-react"

interface StatsCardsProps {
    stats: {
        total: number
        unread: number
        highThreat: number
        today: number
    }
}

export function StatsCards({ stats }: StatsCardsProps) {
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card>
                <CardContent className="p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground font-medium">TOTAL INTELLIGENCE</p>
                        <p className="text-2xl font-bold">{stats.total}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-blue-500 opacity-20" />
                </CardContent>
            </Card>
            <Card>
                <CardContent className="p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground font-medium">UNREAD ALERTS</p>
                        <p className="text-2xl font-bold">{stats.unread}</p>
                    </div>
                    <Bell className="h-8 w-8 text-green-500 opacity-20" />
                </CardContent>
            </Card>
            <Card>
                <CardContent className="p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground font-medium text-red-600">HIGH THREAT</p>
                        <p className="text-2xl font-bold text-red-600">{stats.highThreat}</p>
                    </div>
                    <AlertTriangle className="h-8 w-8 text-red-500 opacity-20" />
                </CardContent>
            </Card>
            <Card>
                <CardContent className="p-4 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-muted-foreground font-medium">TODAY</p>
                        <p className="text-2xl font-bold">{stats.today}</p>
                    </div>
                    <Calendar className="h-8 w-8 text-purple-500 opacity-20" />
                </CardContent>
            </Card>
        </div>
    )
}
