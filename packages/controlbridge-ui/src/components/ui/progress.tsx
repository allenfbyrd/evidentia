import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Minimal progress bar primitive (no Radix dependency; shadcn's usual
 * progress component adds @radix-ui/react-progress which we don't install
 * yet). Accepts a 0-100 `value`; renders a horizontal bar.
 */
const Progress = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { value: number }
>(({ className, value, ...props }, ref) => (
  <div
    ref={ref}
    role="progressbar"
    aria-valuenow={Math.max(0, Math.min(100, value))}
    aria-valuemin={0}
    aria-valuemax={100}
    className={cn(
      "relative h-2 w-full overflow-hidden rounded-full bg-secondary",
      className,
    )}
    {...props}
  >
    <div
      className="h-full bg-primary transition-transform"
      style={{ transform: `translateX(-${100 - Math.max(0, Math.min(100, value))}%)` }}
    />
  </div>
));
Progress.displayName = "Progress";

export { Progress };
