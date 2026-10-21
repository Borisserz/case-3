/** Client-side SVG → PNG download for Liber diagrams. */

export function slugDiagramFilename(title: string, id: string): string {
  const base = (title || id || "diagram")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9а-яё_-]+/gi, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  const safe = base || id || "diagram";
  return safe.endsWith(".png") ? safe : `${safe}.png`;
}

function intrinsicSize(svgEl: SVGSVGElement): { w: number; h: number } {
  const vb = svgEl.viewBox?.baseVal;
  if (vb && vb.width > 0 && vb.height > 0) {
    return { w: Math.ceil(vb.width), h: Math.ceil(vb.height) };
  }
  const attrW = Number(svgEl.getAttribute("width"));
  const attrH = Number(svgEl.getAttribute("height"));
  if (attrW > 0 && attrH > 0) {
    return { w: Math.ceil(attrW), h: Math.ceil(attrH) };
  }
  try {
    const b = svgEl.getBBox();
    if (b.width > 0 && b.height > 0) {
      return { w: Math.ceil(b.width), h: Math.ceil(b.height) };
    }
  } catch {
    /* not in DOM yet */
  }
  const rect = svgEl.getBoundingClientRect();
  return {
    w: Math.max(1, Math.ceil(rect.width || 800)),
    h: Math.max(1, Math.ceil(rect.height || 600)),
  };
}

export async function downloadDiagramPng(
  svgEl: SVGSVGElement,
  filename: string,
): Promise<void> {
  const clone = svgEl.cloneNode(true) as SVGSVGElement;
  if (!clone.getAttribute("xmlns")) {
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  }
  const { w, h } = intrinsicSize(svgEl);
  // Cap export canvas so huge diagrams don't OOM; still sharper than on-screen rail.
  const maxEdge = 2400;
  const scale = Math.min(2, maxEdge / Math.max(w, h));
  const outW = Math.max(1, Math.round(w * scale));
  const outH = Math.max(1, Math.round(h * scale));
  clone.setAttribute("width", String(w));
  clone.setAttribute("height", String(h));
  if (!clone.getAttribute("viewBox")) {
    clone.setAttribute("viewBox", `0 0 ${w} ${h}`);
  }
  const xml = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const img = await loadImage(url);
    const canvas = document.createElement("canvas");
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas unsupported");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, outW, outH);
    const png = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), "image/png"),
    );
    if (!png) throw new Error("png encode failed");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(png);
    const name = filename.endsWith(".png") ? filename : `${filename}.png`;
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("svg image load failed"));
    img.src = url;
  });
}
