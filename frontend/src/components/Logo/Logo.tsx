interface LogoMarkProps {
  size?: number;
  className?: string;
}

export function LogoMark({ size = 32, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="logo-mark-gradient" x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop stopColor="#818CF8" />
          <stop offset="0.5" stopColor="#6366F1" />
          <stop offset="1" stopColor="#7C3AED" />
        </linearGradient>
        <linearGradient id="logo-spark-gradient" x1="18" y1="6" x2="26" y2="14" gradientUnits="userSpaceOnUse">
          <stop stopColor="#C4B5FD" />
          <stop offset="1" stopColor="#A78BFA" />
        </linearGradient>
      </defs>
      <rect x="9" y="5" width="15" height="19" rx="2.5" fill="white" fillOpacity="0.22" />
      <rect x="6" y="8" width="15" height="19" rx="2.5" fill="white" fillOpacity="0.92" />
      <rect x="6" y="8" width="15" height="19" rx="2.5" stroke="url(#logo-mark-gradient)" strokeWidth="0.75" strokeOpacity="0.35" />
      <line x1="10" y1="14" x2="17" y2="14" stroke="url(#logo-mark-gradient)" strokeWidth="1.75" strokeLinecap="round" />
      <line x1="10" y1="17.5" x2="15" y2="17.5" stroke="url(#logo-mark-gradient)" strokeWidth="1.75" strokeLinecap="round" strokeOpacity="0.55" />
      <line x1="10" y1="21" x2="13.5" y2="21" stroke="url(#logo-mark-gradient)" strokeWidth="1.75" strokeLinecap="round" strokeOpacity="0.35" />
      <path
        d="M20.5 6.5L22.8 9.8L26.5 10.3L23.8 12.8L24.5 16.5L20.5 14.6L16.5 16.5L17.2 12.8L14.5 10.3L18.2 9.8L20.5 6.5Z"
        fill="url(#logo-spark-gradient)"
      />
    </svg>
  );
}

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  className?: string;
}

const SIZE_MAP = {
  sm: { container: "h-8 w-8", mark: 20, wordmark: "text-apple-subheadline" },
  md: { container: "h-10 w-10", mark: 24, wordmark: "text-apple-headline" },
  lg: { container: "h-11 w-11", mark: 26, wordmark: "text-apple-title-2" },
} as const;

export function Logo({ size = "md", showWordmark = true, className }: LogoProps) {
  const config = SIZE_MAP[size];

  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <div
        className={`logo-mark ${config.container} flex shrink-0 items-center justify-center rounded-[11px]`}
        data-testid="logo-mark"
      >
        <LogoMark size={config.mark} />
      </div>
      {showWordmark ? (
        <div className="min-w-0 leading-none">
          <p className={`${config.wordmark} font-semibold tracking-tight text-apple-label`}>
            Resume<span className="logo-wordmark-accent">Forge</span>
          </p>
          {size !== "sm" ? (
            <p className="mt-0.5 text-apple-caption text-apple-label-tertiary">AI CV tailoring</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
