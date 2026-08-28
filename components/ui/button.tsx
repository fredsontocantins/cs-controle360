import { cn } from "@/lib/utils";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

const variantStyles = {
  primary: "bg-primary text-white hover:bg-primary-light",
  secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200",
  danger: "bg-danger text-white hover:bg-red-600",
  ghost: "bg-transparent text-gray-600 hover:bg-gray-100",
};

const sizeStyles = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading ? true : undefined}
        className={cn(
          "inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading && (
          <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0" aria-hidden="true" />
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
