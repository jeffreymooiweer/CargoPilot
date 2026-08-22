/**
 * The six icons the notifications speak with.
 *
 * One per kind of toast, plus the close button. They were plain text
 * characters before — a ✓, an ℹ, a bare ! and ? — which read as punctuation
 * rather than as a sign, and sat at whatever weight the font felt like.
 *
 * Two things matter for every icon here and are easy to get wrong:
 *
 * - **`fill="currentColor"`, never a colour of its own.** A toast tints its
 *   icon with its own text colour — emerald for success, red for an error,
 *   amber for a question — and each of those has a second value for the dark
 *   theme. An icon carrying a fixed fill would be a black shape on a dark red
 *   card. These are filled rather than stroked, so the fill is what has to be
 *   inherited; a stroke-based set would need `stroke="currentColor"` instead.
 * - **No `width`/`height` attributes.** The size comes from the class the
 *   caller passes, so the same icon can be 20px in a toast and something else
 *   elsewhere. The `viewBox` stays exactly as drawn — they differ per icon
 *   (24, 466, 512) and that is fine; only the aspect ratio is the icon's own
 *   business.
 *
 * `aria-hidden` on all of them: every toast already says in words what it is,
 * and a screen reader announcing "exclamation circle" before that sentence is
 * noise, not information.
 */

interface IconProps {
  className?: string;
}

/** Success. A bare check — the only one in the set without a circle, which is
 *  why it reads a touch wider than the others at the same size. */
export function CheckIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 465.822 465.822" fill="currentColor" aria-hidden>
      <path d="M5.988,289.981l88.875,88.875c24.992,24.984,65.504,24.984,90.496,0l274.475-274.475c8.185-8.475,7.95-21.98-0.525-30.165c-8.267-7.985-21.374-7.985-29.641,0L155.194,348.691c-8.331,8.328-21.835,8.328-30.165,0l-88.875-88.875c-8.475-8.185-21.98-7.95-30.165,0.525C-1.996,268.608-1.996,281.714,5.988,289.981L5.988,289.981z" />
    </svg>
  );
}

/** An error: an exclamation mark in a circle. */
export function ExclamationIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12,0A12,12,0,1,0,24,12,12.013,12.013,0,0,0,12,0Zm0,22A10,10,0,1,1,22,12,10.011,10.011,0,0,1,12,22Z" />
      <path d="M12,5a1,1,0,0,0-1,1v8a1,1,0,0,0,2,0V6A1,1,0,0,0,12,5Z" />
      <rect x="11" y="17" width="2" height="2" rx="1" />
    </svg>
  );
}

/** Information: an i in a circle. */
export function InfoIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12,0A12,12,0,1,0,24,12,12.013,12.013,0,0,0,12,0Zm0,22A10,10,0,1,1,22,12,10.011,10.011,0,0,1,12,22Z" />
      <path d="M12,10H11a1,1,0,0,0,0,2h1v6a1,1,0,0,0,2,0V12A2,2,0,0,0,12,10Z" />
      <circle cx="12" cy="6.5" r="1.5" />
    </svg>
  );
}

/** A question. A speech bubble rather than a plain question mark: this toast
 *  is not stating something, it is asking the user and waiting. */
export function QuestionIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M11.904,16c.828,0,1.5,.672,1.5,1.5s-.672,1.5-1.5,1.5-1.5-.672-1.5-1.5,.672-1.5,1.5-1.5Zm1-2c0-.561,.408-1.225,.928-1.512,1.5-.826,2.307-2.523,2.009-4.223-.283-1.613-1.607-2.938-3.221-3.221-1.182-.204-2.38,.112-3.289,.874-.907,.763-1.428,1.879-1.428,3.063,0,.553,.448,1,1,1s1-.447,1-1c0-.592,.26-1.15,.714-1.532,.461-.386,1.052-.542,1.657-.435,.787,.138,1.458,.81,1.596,1.596,.153,.871-.241,1.705-1.004,2.125-1.156,.637-1.963,1.979-1.963,3.264,0,.553,.448,1,1,1s1-.447,1-1Zm11.096,5v-6.66C24,5.861,19.096,.454,12.836,.028,9.361-.202,5.961,1.066,3.509,3.521,1.057,5.977-.211,9.378,.03,12.854c.44,6.354,6.052,11.146,13.054,11.146h5.917c2.757,0,5-2.243,5-5ZM12.701,2.024c5.215,.354,9.299,4.885,9.299,10.315v6.66c0,1.654-1.346,3-3,3h-5.917c-6.035,0-10.686-3.904-11.059-9.284-.201-2.899,.855-5.735,2.899-7.781,1.882-1.885,4.435-2.934,7.092-2.934,.228,0,.457,.008,.685,.023Z" />
    </svg>
  );
}

/** Working on it. An open arc, so that spinning it reads as motion — a closed
 *  ring would turn without appearing to. The rotation is the caller's, with
 *  `animate-spin`. */
export function SpinnerIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 512.001 512.001" fill="currentColor" aria-hidden>
      <path d="M268.078,512C126.693,511.962,12.108,397.316,12.146,255.932S126.83-0.038,268.215,0c96.559,0.026,184.888,54.38,228.428,140.565c7.695,15.91,1.035,35.046-14.875,42.74c-15.501,7.497-34.155,1.384-42.213-13.834C391.771,74.81,276.296,36.808,181.634,84.592S48.97,247.851,96.754,342.513s163.259,132.664,257.921,84.88c36.48-18.414,66.133-47.987,84.646-84.417c8.018-15.753,27.287-22.023,43.04-14.005c15.753,8.018,22.023,27.287,14.005,43.04l0,0C452.852,458.077,364.519,512.244,268.078,512z" />
    </svg>
  );
}

/** Close. Used on the dismiss button, which carries its own aria-label. */
export function CircleXmarkIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="m15.707,9.707l-2.293,2.293,2.293,2.293c.391.391.391,1.023,0,1.414-.195.195-.451.293-.707.293s-.512-.098-.707-.293l-2.293-2.293-2.293,2.293c-.195.195-.451.293-.707.293s-.512-.098-.707-.293c-.391-.391-.391-1.023,0-1.414l2.293-2.293-2.293-2.293c-.391-.391-.391-1.023,0-1.414s1.023-.391,1.414,0l2.293,2.293,2.293-2.293c.391-.391,1.023-.391,1.414,0s.391,1.023,0,1.414Zm8.293,2.293c0,6.617-5.383,12-12,12S0,18.617,0,12,5.383,0,12,0s12,5.383,12,12Zm-2,0c0-5.514-4.486-10-10-10S2,6.486,2,12s4.486,10,10,10,10-4.486,10-10Z" />
    </svg>
  );
}
