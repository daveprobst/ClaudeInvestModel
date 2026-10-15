// Client-side statistics so the performance explorer can re-base to any start month.
export type Win = { cagr: number; maxDd: number; vol: number; sharpe: number; ulcer: number; final: number }

export function windowStats(idx: number[], cash: number[], from: number, to: number): Win {
  const n = to - from
  const rets: number[] = []
  const ex: number[] = []
  let peak = 1, maxDd = 0, ssq = 0
  for (let i = from + 1; i <= to; i++) {
    const r = idx[i] / idx[i - 1] - 1
    const c = cash[i] / cash[i - 1] - 1
    rets.push(r); ex.push(r - c)
    const v = idx[i] / idx[from]
    peak = Math.max(peak, v)
    const dd = v / peak - 1
    maxDd = Math.min(maxDd, dd); ssq += dd * dd
  }
  const mean = (a: number[]) => a.reduce((s, x) => s + x, 0) / a.length
  const sd = (a: number[]) => { const m = mean(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)) }
  const final = idx[to] / idx[from]
  return {
    cagr: Math.pow(final, 12 / n) - 1, maxDd, vol: sd(rets) * Math.sqrt(12),
    sharpe: (mean(ex) / sd(ex)) * Math.sqrt(12), ulcer: 100 * Math.sqrt(ssq / n), final,
  }
}

export function drawdownSeries(idx: number[], from: number, to: number): number[] {
  const out: number[] = []
  let peak = 0
  for (let i = from; i <= to; i++) { peak = Math.max(peak, idx[i]); out.push(idx[i] / peak - 1) }
  return out
}
