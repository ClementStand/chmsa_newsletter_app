'use client'

import { useState, useRef, useEffect } from 'react'
import { cn } from "@/lib/utils"

interface CompetitorLogoProps {
    name: string
    website?: string | null
    className?: string
}

export function CompetitorLogo({ name, website, className }: CompetitorLogoProps) {
    if (!name) {
        return <div className={cn("bg-slate-800 animate-pulse", className)} />
    }

    const [fallbackStage, setFallbackStage] = useState(0)
    const [isLoading, setIsLoading] = useState(true)
    const imgRef = useRef<HTMLImageElement>(null)

    const getLogoUrl = (url: string | null | undefined, stage: number) => {
        if (!url || url.trim() === '') return null
        try {
            const cleanUrl = url.trim()
            const fullUrl = cleanUrl.startsWith('http') ? cleanUrl : `https://${cleanUrl}`
            const domain = new URL(fullUrl).hostname

            if (stage === 0) return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`
            return null
        } catch (error) {
            return null
        }
    }

    const handleError = () => {
        setIsLoading(false)
        setFallbackStage((prev) => prev + 1)
    }

    const handleLoad = () => {
        setIsLoading(false)
    }

    // Check if image is already loaded (from cache)
    useEffect(() => {
        if (imgRef.current?.complete) {
            setIsLoading(false)
        }
    }, [])

    const logoUrl = getLogoUrl(website, fallbackStage)

    if (!logoUrl || fallbackStage >= 1) {
        const initials = name.substring(0, 2).toUpperCase()
        return (
            <div
                className={cn(
                    "bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center font-bold text-slate-100 overflow-hidden border border-slate-600",
                    className
                )}
                title={name}
            >
                {initials}
            </div>
        )
    }

    return (
        <div className={cn("relative overflow-hidden", className)}>
            {isLoading && (
                <div className="absolute inset-0 bg-slate-800 animate-pulse z-10" />
            )}
            <img
                ref={imgRef}
                key={logoUrl}
                src={logoUrl}
                alt={name}
                className="w-full h-full object-contain bg-white rounded-full"
                onError={handleError}
                onLoad={handleLoad}
            />
        </div>
    )
}
