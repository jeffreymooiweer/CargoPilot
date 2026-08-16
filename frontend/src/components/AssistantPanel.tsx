import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, AssistantEvent, AssistantPending, AssistantState } from "../api/client";
import { documentLanguage, localised } from "../i18n/language";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

interface Chip {
  label: string;
  send: string;
}

interface Props {
  /** The wizard state as the assistant sees it; built by the wizard page. */
  buildState: () => AssistantState;
  /** The patched state coming back; the wizard page maps it onto its own. */
  onApplyState: (state: AssistantState) => void;
  /** Chat-first: a description typed before the wizard opened; sent once. */
  initialMessage?: string | null;
}

/** The chat beside the wizard.
 *
 * Every sentence the assistant says is a translation of something the backend
 * produced: a parsed goods line, a substance the name recognition offered, an
 * open question `dg/prepare` named, a document field the registry requires.
 * The texts come from the same four-language sources the wizard itself uses —
 * so the chat can never promise anything the form does not show.
 */
export default function AssistantPanel({ buildState, onApplyState, initialMessage }: Props) {
  const { t, i18n } = useTranslation();
  const lang = documentLanguage(i18n.language);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", text: t("assistant.intro") },
  ]);
  const [chips, setChips] = useState<Chip[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const pendingRef = useRef<AssistantPending | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);
  // The chat-first sentence is sent exactly once, when the panel mounts.
  const initialSent = useRef(false);
  useEffect(() => {
    if (initialSent.current || !initialMessage?.trim()) return;
    initialSent.current = true;
    void send(initialMessage.trim());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage]);

  const push = (message: ChatMessage) =>
    setMessages((current) => [...current, message]);

  const optionChips = (pending: AssistantPending): Chip[] => {
    const labels = (pending.option_labels ?? {}) as Record<string, unknown>;
    const result: Chip[] = (pending.options ?? []).map((option) => {
      const label = labels[option];
      return {
        label:
          (label && typeof label === "object"
            ? localised(label as Record<string, string>, lang)
            : (label as string)) || option,
        send: option,
      };
    });
    if (pending.scope !== "un_confirm" && pending.required === false) {
      result.push({ label: t("assistant.skip"), send: "skip" });
    }
    return result;
  };

  const verbalise = (event: AssistantEvent): string | null => {
    switch (event.kind) {
      case "lines_added":
        return t("assistant.linesAdded", { count: Number(event.count ?? 0) });
      case "un_question": {
        const candidates = (event.candidates ?? []) as {
          un: string; name: string; class: string;
        }[];
        if (candidates.length === 1) {
          const c = candidates[0];
          return t("assistant.unConfirmOne", { un: c.un, name: c.name, class: c.class });
        }
        return t("assistant.unConfirmMany", {
          list: candidates.map((c) => `UN ${c.un} ${c.name}`).join("; "),
        });
      }
      case "un_confirmed":
        return t("assistant.unConfirmed", { un: String(event.un ?? "") });
      case "un_dismissed":
        return t("assistant.unDismissed");
      case "dg_question":
      case "doc_question": {
        const label =
          localised(event.label as Record<string, string> | undefined, lang) ||
          String(event.field ?? "");
        const reasonKey = `dgopen.${String(event.reason ?? "")}`;
        const reason = event.reason ? t(reasonKey as "dgopen.sp274") : "";
        const question = t("assistant.question", { label });
        return reason && reason !== reasonKey ? `${question} (${reason})` : question;
      }
      case "ready":
        return t("assistant.ready");
      case "not_understood":
        return t("assistant.notUnderstood");
      default:
        return null;
    }
  };

  const send = async (text: string, display?: string) => {
    const shown = (display ?? text).trim();
    if (!shown || busy) return;
    push({ role: "user", text: shown });
    setInput("");
    setChips([]);
    setBusy(true);
    try {
      const result = await api.assistantStep({
        message: text,
        state: buildState(),
        pending: pendingRef.current,
        language: lang,
      });
      onApplyState(result.state);
      pendingRef.current = result.pending ?? null;
      for (const event of result.events) {
        const line = verbalise(event);
        if (line) push({ role: "assistant", text: line });
      }
      setChips(result.pending ? optionChips(result.pending) : []);
    } catch (e) {
      push({ role: "assistant", text: String(e) });
    } finally {
      setBusy(false);
      window.setTimeout(() => {
        logRef.current?.scrollTo?.({ top: logRef.current.scrollHeight });
      }, 0);
    }
  };

  return (
    <div className={`${panelClass} flex flex-col p-4`} data-testid="assistant-panel">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        {t("assistant.title")}
      </h3>
      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{t("assistant.subtitle")}</p>
      <div ref={logRef} className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
        {messages.map((message, index) => (
          <div
            key={index}
            className={
              message.role === "user"
                ? "ml-8 rounded-xl bg-brand-600 px-3 py-2 text-sm text-white"
                : "mr-8 rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-800 dark:bg-slate-800 dark:text-slate-100"
            }
          >
            {message.text}
          </div>
        ))}
      </div>
      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {chips.map((chip) => (
            <button
              key={chip.send}
              type="button"
              disabled={busy}
              onClick={() => void send(chip.send, chip.label)}
              className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {chip.label}
            </button>
          ))}
        </div>
      )}
      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void send(input);
        }}
      >
        <input
          className="min-h-[40px] w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          value={input}
          placeholder={t("assistant.placeholder")}
          onChange={(event) => setInput(event.target.value)}
          disabled={busy}
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {t("assistant.send")}
        </button>
      </form>
    </div>
  );
}
