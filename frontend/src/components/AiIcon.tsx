/** The assistant's icon: a rounded frame reading "AI", its border giving way
 *  at the corner where the spark sits. Drawn inline so it follows
 *  `currentColor` in both themes and needs no asset. */
export default function AiIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={className}>
      <path
        d="M13.2 20.25 H7.5 A3.75 3.75 0 0 1 3.75 16.5 V7.5 A3.75 3.75 0 0 1 7.5 3.75 H16.5 A3.75 3.75 0 0 1 20.25 7.5 V13.2"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      <path
        d="M6.9 15.6 L9.7 7.6 L12.5 15.6 M7.9 12.9 H11.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M15.1 7.6 V15.6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path
        d="M18.6 13.9 Q19.15 17.45 22.7 18 Q19.15 18.55 18.6 22.1 Q18.05 18.55 14.5 18 Q18.05 17.45 18.6 13.9 Z"
        fill="currentColor"
      />
    </svg>
  );
}
