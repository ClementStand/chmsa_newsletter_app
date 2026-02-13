"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
    value?: number[]
    onValueChange?: (value: number[]) => void
    max?: number
    min?: number
    step?: number
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
    ({ className, value, onValueChange, max, min, step, ...props }, ref) => {
        const val = value ? value[0] : (min || 0)

        const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            onValueChange?.([parseFloat(e.target.value)])
        }

        return (
            <input
                type="range"
                className={cn(
                    "w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600",
                    className
                )}
                ref={ref}
                value={val}
                max={max}
                min={min}
                step={step}
                onChange={handleChange}
                {...props}
            />
        )
    }
)
Slider.displayName = "Slider"

export { Slider }
