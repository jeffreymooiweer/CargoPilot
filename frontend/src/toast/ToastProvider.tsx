/** The one notification mechanism.
 *
 * Before this existed the application spoke through 87 inline notices in
 * eleven files, four native `confirm()` popups and one hand-built update
 * toast — three visual languages for one sentence: "that worked" (or it did
 * not). This provider replaces the transient half of that. What it does NOT
 * replace is deliberate: field validation stays at the field, sign-in errors
 * stay on the form, and regulatory findings stay inline forever — a safety
 * warning that slides away after four seconds is exactly the failure this
 * application is built against.
 *
 * Four kinds, each with its own lifetime:
 *
 * - `success` / `info` dismiss themselves after four seconds;
 * - `error` stays until the user closes it — a missed network error is a
 *   document that silently never went out;
 * - `loading` stays until the caller resolves it into success or error, so a
 *   slow action holds exactly one toast from "working…" to its outcome.
 *
 * `undoable` is the deferred-action pattern the delete flows use: the UI
 * updates immediately, the real API call fires only when the undo window
 * closes (timer, manual dismiss, or a sixth toast pushing the queue). Undo
 * within the window means the call never happens — which is why a deleted
 * user keeps their password: nothing was deleted yet. A full page reload
 * inside the window abandons the pending call and the item survives; that is
 * the accepted edge of the pattern, preferred over deleting behind the
 * user's back on their way out.
 *
 * Self-built rather than a dependency: the frontend carries five runtime
 * dependencies by policy, and this is ~150 lines of behaviour we can pin
 * with tests of our own.
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";

export type ToastKind = "success" | "info" | "error" | "loading" | "question";

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
  /**
   * Buttons in the toast: the undo, or an answer to a question.
   *
   * Several of them because a question can have several right answers — two
   * sulphuric acids differing only in their qualifier are one recognition
   * with two UN numbers, and picking between them is the whole point.
   */
  actions?: ToastAction[];
  /** For undoable toasts: what to do when the window closes unused. */
  onExpire?: () => void;
  /** Fires only on the explicit × — not on timeout or eviction. The update
   * notice uses this to remember "seen" per version: being pushed out by
   * other toasts is not the admin saying they read it. */
  onDismiss?: () => void;
  /** Info toasts that must not auto-dismiss (the update notice). */
  sticky?: boolean;
}

interface UndoableOptions {
  /** Fires when the undo window closes without the undo being taken —
   * this is where the real API call lives. */
  execute: () => void;
  /** Fires when the user clicks undo — restore the optimistic UI. */
  restore: () => void;
  label?: string;
}

export interface ToastApi {
  success: (message: string) => number;
  info: (
    message: string,
    options?: { sticky?: boolean; actions?: ToastAction[]; onDismiss?: () => void },
  ) => number;
  error: (message: string) => number;
  /**
   * A question the user has to answer, with the answers as buttons.
   *
   * Always stays: a question that slides away after four seconds has not been
   * asked. Closing it with the × is itself an answer — "no" — which is what
   * `onDismiss` is for.
   */
  ask: (message: string, options: { actions: ToastAction[]; onDismiss?: () => void }) => number;
  /** Returns a handle that resolves the loading toast into its outcome.
   * `progress` rewrites the message while still loading — one toast follows
   * a multi-phase action (pulling the image, restarting) instead of a new
   * toast per phase. */
  loading: (message: string) => {
    id: number;
    progress: (message: string) => void;
    success: (message: string) => void;
    error: (message: string) => void;
  };
  undoable: (message: string, options: UndoableOptions) => number;
  dismiss: (id: number) => void;
}

const AUTO_DISMISS_MS = 4000;
export const UNDO_WINDOW_MS = 6000;
/** More than this and the oldest dismissable one is closed first: a stack of
 * stale confirmations buries the one the user is looking for. */
const MAX_VISIBLE = 5;

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) throw new Error("useToast outside ToastProvider");
  return api;
}

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<Toast[]>([]);
  // Timers live outside state: a re-render must not reset a running window.
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const remove = useCallback((id: number, reason: "undo" | "timeout" | "dismiss") => {
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
    timers.current.delete(id);
    setToasts((current) => {
      const found = current.find((toast) => toast.id === id);
      // Closing an undoable toast in any way except the undo button means
      // "I don't need the undo": the deferred action fires now rather than
      // silently never.
      if (reason !== "undo") found?.onExpire?.();
      if (reason === "dismiss") found?.onDismiss?.();
      return current.filter((toast) => toast.id !== id);
    });
  }, []);

  const push = useCallback(
    (toast: Omit<Toast, "id">, lifetimeMs: number | null) => {
      const id = nextId++;
      setToasts((current) => {
        const next = [...current, { ...toast, id }];
        if (next.length > MAX_VISIBLE) {
          // A loading toast is a promise to the user and only its own outcome
          // may close it, so it is never the one that gives way.
          const evictable = next.filter((candidate) => candidate.kind !== "loading");
          // Transient confirmations give way before anything that stays on
          // purpose. A sticky toast is either a question waiting for an answer
          // or a notice meant to be read; pushing one of those out to make
          // room for "saved" loses the more important of the two.
          const oldest =
            evictable.find((candidate) => !candidate.sticky) ?? evictable[0];
          if (oldest) {
            // Deferred actions still fire — being pushed out of view must not
            // cancel a delete the user asked for.
            oldest.onExpire?.();
            const timer = timers.current.get(oldest.id);
            if (timer) clearTimeout(timer);
            timers.current.delete(oldest.id);
            return next.filter((candidate) => candidate.id !== oldest.id);
          }
        }
        return next;
      });
      if (lifetimeMs !== null) {
        timers.current.set(id, setTimeout(() => remove(id, "timeout"), lifetimeMs));
      }
      return id;
    },
    [remove],
  );

  const api = useMemo<ToastApi>(() => {
    const update = (id: number, patch: Partial<Toast>, lifetimeMs: number | null) => {
      setToasts((current) =>
        current.map((toast) => (toast.id === id ? { ...toast, ...patch } : toast)),
      );
      const timer = timers.current.get(id);
      if (timer) clearTimeout(timer);
      if (lifetimeMs !== null) {
        timers.current.set(id, setTimeout(() => remove(id, "timeout"), lifetimeMs));
      }
    };
    return {
      success: (message) => push({ kind: "success", message }, AUTO_DISMISS_MS),
      info: (message, options) =>
        push(
          {
            kind: "info",
            message,
            sticky: options?.sticky,
            actions: options?.actions,
            onDismiss: options?.onDismiss,
          },
          options?.sticky ? null : AUTO_DISMISS_MS,
        ),
      error: (message) => push({ kind: "error", message }, null),
      ask: (message, { actions, onDismiss }) =>
        push({ kind: "question", message, sticky: true, actions, onDismiss }, null),
      loading: (message) => {
        const id = push({ kind: "loading", message }, null);
        return {
          id,
          progress: (next: string) => update(id, { message: next }, null),
          success: (outcome: string) =>
            update(id, { kind: "success", message: outcome }, AUTO_DISMISS_MS),
          error: (outcome: string) => update(id, { kind: "error", message: outcome }, null),
        };
      },
      undoable: (message, { execute, restore, label }) => {
        let done = false;
        const once = (fn: () => void) => () => {
          if (done) return;
          done = true;
          fn();
        };
        const id: number = push(
          {
            kind: "info",
            message,
            onExpire: once(execute),
            actions: [
              {
                label: label ?? t("toast.undo"),
                run: once(() => {
                  restore();
                  remove(id, "undo");
                }),
              },
            ],
          },
          UNDO_WINDOW_MS,
        );
        return id;
      },
      dismiss: (id) => remove(id, "dismiss"),
    };
  }, [push, remove, t]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastHost toasts={toasts} onDismiss={(id) => remove(id, "dismiss")} />
    </ToastContext.Provider>
  );
}

const KIND_STYLE: Record<ToastKind, string> = {
  success:
    "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-700 dark:bg-emerald-950 dark:text-emerald-100",
  info: "border-slate-300 bg-white text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100",
  error:
    "border-red-300 bg-red-50 text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100",
  loading:
    "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-700 dark:bg-sky-950 dark:text-sky-100",
  // Amber, like the recognition chip it replaces: this one is not telling the
  // user something, it is waiting for them.
  question:
    "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100",
};

const KIND_ICON: Record<ToastKind, string> = {
  success: "✓",
  info: "ℹ",
  error: "!",
  loading: "…",
  question: "?",
};

function ToastHost({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  const { t } = useTranslation();
  if (toasts.length === 0) return null;
  return (
    // Bottom sheet on mobile, bottom-right stack on desktop. Errors announce
    // assertively; the rest waits its turn — a screen reader user saving a
    // form should not be interrupted mid-sentence for "saved".
    <div className="fixed inset-x-0 bottom-0 z-50 flex flex-col gap-2 p-3 sm:inset-x-auto sm:right-4 sm:bottom-4 sm:w-96">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role={toast.kind === "error" ? "alert" : "status"}
          aria-live={toast.kind === "error" ? "assertive" : "polite"}
          className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-sm shadow-lg ${KIND_STYLE[toast.kind]}`}
        >
          <span aria-hidden className={`mt-0.5 shrink-0 font-semibold ${toast.kind === "loading" ? "animate-pulse" : ""}`}>
            {KIND_ICON[toast.kind]}
          </span>
          {/* A question puts its answers under the text rather than beside it:
              two or three UN numbers on one line squeeze the sentence that
              says what is being asked. One answer still sits alongside, where
              "Undo" has always been. */}
          <div className={`min-w-0 flex-1 ${(toast.actions?.length ?? 0) > 1 ? "space-y-1.5" : ""}`}>
            <span className="block break-words">{toast.message}</span>
            {(toast.actions?.length ?? 0) > 1 && (
              <div className="flex flex-wrap gap-1.5">
                {toast.actions!.map((action) => (
                  <button
                    key={action.label}
                    type="button"
                    onClick={action.run}
                    className="rounded-md border border-current px-2 py-0.5 text-[11px] font-semibold hover:opacity-75"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          {toast.actions?.length === 1 && (
            <button
              type="button"
              onClick={toast.actions[0].run}
              className="shrink-0 rounded-md px-2 py-0.5 font-semibold underline decoration-2 underline-offset-2 hover:opacity-75"
            >
              {toast.actions[0].label}
            </button>
          )}
          {toast.kind !== "loading" && (
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              aria-label={t("toast.dismiss")}
              className="shrink-0 rounded-md px-1.5 text-lg leading-none opacity-60 hover:opacity-100"
            >
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
