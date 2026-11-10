import en from "./i18n/en.json";
import fr from "./i18n/fr.json";
import { canManuallyRetry, type PublicResult } from "./scoring-api.js";

export type UiLanguage = "en" | "fr";

export interface ResultPresentation {
  statusLabel: string;
  headline: string;
  scoreLine?: string;
  verdictLine?: string;
  qualifier?: string;
  evidenceLine: string;
  engineLine: string;
  reasonLine?: string;
  signals: string[];
  accessibleLabel: string;
  retryAvailable: boolean;
}

export function presentResult(result: PublicResult, language: UiLanguage): ResultPresentation {
  const copy = language === "fr" ? fr : en;
  const engine = result.engine === "SIGNALS_ONLY" ? copy.ui.signalsOnlyEngine : copy.ui.modelEngine;
  const engineLine = `${copy.ui.engineLabel}: ${engine}`;
  const evidence = result.evidenceQuality === "LOW"
    ? copy.ui.lowEvidence
    : result.evidenceQuality === "ADEQUATE" ? copy.signal.adequateEvidence : copy.ui.noEvidence;
  const evidenceLine = `${copy.ui.evidenceLabel}: ${evidence}`;
  const signals = result.signals.map((signal) => {
    const key = signal.kind as keyof typeof copy.signal;
    return copy.signal[key] ?? signal.summary;
  });

  if (result.status === "SCORED" && typeof result.trustScore === "number" && typeof result.verdict === "string") {
    const verdict = copy.band[result.verdict as keyof typeof en.band];
    const scoreLine = `${copy.ui.scoreLabel}: ${result.trustScore}/100`;
    const verdictLine = `${copy.ui.verdictLabel}: ${verdict}`;
    const qualifier = result.evidenceQuality === "LOW" ? copy.ui.lowEvidence : undefined;
    const accessibleLabel = [
      copy.ui.scoredStatus, scoreLine, verdictLine, evidenceLine, engineLine,
      signals.length ? `${copy.ui.detailsAction}: ${signals.join(", ")}` : "",
    ].filter(Boolean).join(". ");
    return {
      statusLabel: copy.ui.scoredStatus,
      headline: `${result.trustScore}/100 · ${verdict}`,
      scoreLine,
      verdictLine,
      qualifier,
      evidenceLine,
      engineLine,
      signals,
      accessibleLabel,
      retryAvailable: false,
    };
  }

  if (result.status === "SIGNALS_ONLY") {
    const accessibleLabel = [
      copy.ui.signalsOnlyStatus, copy.ui.noScore, copy.ui.noVerdict,
      evidenceLine, engineLine,
      signals.length ? `${copy.ui.detailsAction}: ${signals.join(", ")}` : "",
    ].filter(Boolean).join(". ");
    return {
      statusLabel: copy.ui.signalsOnlyStatus,
      headline: copy.ui.signalOnlyMode,
      evidenceLine,
      engineLine,
      signals,
      accessibleLabel,
      retryAvailable: false,
    };
  }

  const reason = result.reasonCode === "SCORING_TIMEOUT" ? copy.ui.timeout
    : result.reasonCode === "SCORING_UNAVAILABLE" ? copy.ui.unavailable
      : result.reasonCode === "INSUFFICIENT_TEXT" ? copy.ui.insufficientText
        : result.reasonCode === "UNSUPPORTED_LANGUAGE" ? copy.ui.unsupportedLanguage
          : copy.ui.unknownHeading;
  const reasonLine = `${copy.ui.reasonLabel}: ${reason}`;
  return {
    statusLabel: copy.ui.unknownStatus,
    headline: copy.ui.unknownHeading,
    evidenceLine,
    engineLine,
    reasonLine,
    signals,
    accessibleLabel: [
      copy.ui.unknownStatus, copy.ui.noScore, copy.ui.noVerdict,
      reasonLine, evidenceLine, engineLine,
    ].join(". "),
    retryAvailable: canManuallyRetry(result),
  };
}
