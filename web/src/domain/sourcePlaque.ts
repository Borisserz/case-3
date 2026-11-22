/** Hide the document chip. The attached text and file stay for the next send. */

export function hideSourcePlaque<TDraft, TFile>(state: {
  sourceDraft: TDraft | null;
  file: TFile | null;
}): {
  plaqueDismissed: true;
  sourceDraft: TDraft | null;
  file: TFile | null;
} {
  return {
    plaqueDismissed: true,
    sourceDraft: state.sourceDraft,
    file: state.file,
  };
}
