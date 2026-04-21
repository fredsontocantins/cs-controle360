import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'warning' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

    const variants = {
      primary: 'bg-[#0d3b66] text-white hover:bg-[#1a5a9a] focus:ring-[#0d3b66]',
      secondary: 'bg-gray-500 text-white hover:bg-gray-600 focus:ring-gray-500',
      danger: 'bg-[#f44336] text-white hover:bg-red-600 focus:ring-[#f44336]',
      success: 'bg-[#4CAF50] text-white hover:bg-green-600 focus:ring-[#4CAF50]',
      warning: 'bg-[#f59e0b] text-white hover:bg-amber-600 focus:ring-[#f59e0b]',
      outline: 'border-2 border-[#0d3b66] text-[#0d3b66] hover:bg-[#0d3b66] hover:text-white focus:ring-[#0d3b66]',
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    };

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
