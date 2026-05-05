import { cn } from "@/lib/utils";
import { forwardRef, useId } from "react";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: Array<{ value: string; label: string }>;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className, id: providedId, required, ...props }, ref) => {
    const generatedId = useId();
    const id = providedId || generatedId;
    const errorId = `${id}-error`;

    return (
      <div className="space-y-1">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-700">
            {label}
            {required && <span className="text-red-500 ml-1" aria-hidden="true">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          required={required}
          aria-invalid={!!error}
          aria-describedby={error ? errorId : undefined}
          className={cn(
            "block w-full px-3 py-2 border border-border rounded-md shadow-sm text-sm",
            "focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
            "disabled:bg-gray-50 disabled:text-gray-500",
            error && "border-danger focus:ring-danger focus:border-danger",
            className
          )}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={errorId} className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";
