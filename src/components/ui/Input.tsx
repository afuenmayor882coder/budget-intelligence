import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-secondary mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tertiary w-4 h-4">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              'w-full h-8 rounded-lg bg-surface border text-sm text-primary placeholder:text-tertiary',
              'transition-colors duration-150',
              'focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:ring-opacity-30 focus:border-[var(--accent-blue)]',
              icon ? 'pl-8 pr-3' : 'px-3',
              error ? 'border-[var(--accent-red)]' : 'border-[var(--border)]',
              className
            )}
            {...props}
          />
        </div>
        {error && <p className="mt-1 text-xs text-accent-red">{error}</p>}
      </div>
    )
  }
)
Input.displayName = 'Input'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: { value: string; label: string }[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className, id, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-secondary mb-1.5">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={cn(
            'w-full h-8 rounded-lg bg-surface border text-sm text-primary',
            'transition-colors duration-150 cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:ring-opacity-30',
            'px-3 appearance-none',
            error ? 'border-[var(--accent-red)]' : 'border-[var(--border)]',
            className
          )}
          {...props}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value} className="bg-[var(--surface)]">
              {o.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1 text-xs text-accent-red">{error}</p>}
      </div>
    )
  }
)
Select.displayName = 'Select'
