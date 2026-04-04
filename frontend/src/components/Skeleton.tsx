type SkeletonVariant = 'card' | 'list' | 'text';

interface SkeletonProps {
  variant?: SkeletonVariant;
  className?: string;
}

const baseClass = 'animate-pulse rounded bg-gray-200';

export function Skeleton({ variant = 'text', className = '' }: SkeletonProps) {
  if (variant === 'card') {
    return (
      <div className={`space-y-3 ${className}`} aria-label="Loading" role="status">
        <div className={`${baseClass} h-40 w-full rounded-lg`} />
        <div className={`${baseClass} h-4 w-3/4`} />
        <div className={`${baseClass} h-4 w-1/2`} />
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className={`space-y-2 ${className}`} aria-label="Loading" role="status">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className={`${baseClass} h-10 w-10 rounded-full`} />
            <div className="flex-1 space-y-1.5">
              <div className={`${baseClass} h-3.5 w-2/3`} />
              <div className={`${baseClass} h-3 w-1/3`} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // text variant
  return (
    <div className={`space-y-2 ${className}`} aria-label="Loading" role="status">
      <div className={`${baseClass} h-4 w-full`} />
      <div className={`${baseClass} h-4 w-5/6`} />
      <div className={`${baseClass} h-4 w-4/6`} />
    </div>
  );
}
