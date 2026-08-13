/**
 * The exporter's warnings, surfaced on the document card before the download.
 *
 * `validate_document` on the backend has always returned (errors, warnings).
 * The errors work — export refuses with a 422. The warnings were computed and
 * discarded: the export route ignored them (a file response has no body to
 * carry them) and POST /documents/validate, which does return them, was never
 * called from this codebase. Fourteen warning sites fed a dead channel,
 * including the missing-unit notice against ADR 5.4.1.1.1 (f), the lost
 * 1.1.3.6 exemption, and the VGM mass check.
 *
 * Hence this pair: a hook that asks the validate endpoint for every document on
 * the export step, and a list that renders the answer on the card — *before*
 * the download button, because a warning shown after the file is on disk is a
 * warning shown too late. Warnings never disable the button; that distinction
 * from errors is the point of having two lists.
 */
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { DocumentExportPayload } from "../api/client";

/** Warnings per document key, straight from the validate endpoint.
 *
 *  The texts arrive already localised — validation is asked in the document's
 *  output language — so nothing here translates anything.
 *
 *  The effect keys on the *content* of the payloads, not their identity: the
 *  caller rebuilds the array every render, and an effect that fired on identity
 *  would turn every keystroke into a round of validation requests. A failing
 *  endpoint yields no warnings rather than an error, because a validation that
 *  cannot run must not take the export step down with it — the download works
 *  without it and errors have their own channel.
 */
export function useDocumentValidation(
  payloads: DocumentExportPayload[],
  active: boolean,
): Record<string, string[]> {
  const [warnings, setWarnings] = useState<Record<string, string[]>>({});
  const current = useRef(payloads);
  current.current = payloads;
  const contentKey = JSON.stringify(payloads);

  useEffect(() => {
    if (!active || current.current.length === 0) {
      setWarnings({});
      return;
    }
    let cancelled = false;
    Promise.all(
      current.current.map((payload) =>
        api
          .validateDocument(payload)
          .then((result) => [payload.document_key, result.warnings] as const)
          .catch(() => [payload.document_key, [] as string[]] as const),
      ),
    ).then((entries) => {
      if (!cancelled) setWarnings(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
  }, [active, contentKey]);

  return warnings;
}

export default function DocumentWarnings({
  heading,
  warnings,
}: {
  heading: string;
  warnings: string[];
}) {
  if (warnings.length === 0) return null;
  return (
    <div className="mt-1 text-xs text-amber-600 dark:text-amber-300">
      <p className="font-medium">{heading}</p>
      <ul className="mt-0.5 list-disc space-y-0.5 pl-4">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </div>
  );
}
