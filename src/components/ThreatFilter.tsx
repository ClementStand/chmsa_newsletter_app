'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useState, useEffect } from 'react'
import { Slider } from "@/components/ui/slider"

export default function ThreatFilter({ currentLevel }: { currentLevel: number }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [localLevel, setLocalLevel] = useState(currentLevel)
  const [debouncedLevel, setDebouncedLevel] = useState(currentLevel)

  // Sync local state if prop changes (e.g. from refresh or direct nav)
  useEffect(() => {
    setLocalLevel(currentLevel)
  }, [currentLevel])

  // Debounce the filtering action
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedLevel(localLevel)
    }, 500) // 500ms debounce

    return () => clearTimeout(timer)
  }, [localLevel])

  // Trigger navigation only when debounced value changes
  useEffect(() => {
    if (debouncedLevel !== currentLevel) {
      const params = new URLSearchParams(searchParams.toString())
      params.set('minThreat', debouncedLevel.toString())
      router.push(`/?${params.toString()}`)
    }
  }, [debouncedLevel, router, searchParams, currentLevel])

  return (
    <div className="w-48">
      <div className="flex justify-between text-xs font-medium text-slate-400 mb-2">
        <span>Min Threat Level</span>
        <span className="text-cyan-400 font-bold">{localLevel}+</span>
      </div>
      <Slider
        value={[localLevel]}
        max={5}
        min={1}
        step={1}
        onValueChange={(val) => setLocalLevel(val[0])}
        className="cursor-pointer"
      />
    </div>
  )
}
