export const pct = (x: number | null | undefined, d = 1, sign = false) => {
  if (x == null || Number.isNaN(x)) return '–'
  let t = (x * 100).toFixed(d)
  if (/^-0(\.0+)?$/.test(t)) t = t.slice(1)            // avoid "−0.0%"
  return `${sign && Number(t) > 0 ? '+' : ''}${t.replace('-', '−')}%`
}
export const num = (x: number | null | undefined, d = 2) => (x == null || Number.isNaN(x) ? '–' : x.toFixed(d).replace('-', '−'))
export const mult = (x: number, d = 0) => `${x.toLocaleString('en-US', { maximumFractionDigits: d })}×`
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const monthLabel = (ym: string) => {
  const [y, m] = ym.split('-')
  return `${MONTHS[Number(m) - 1]} ${y}`
}
export const ymToNum = (ym: string) => { const [y, m] = ym.split('-').map(Number); return y + (m - 1) / 12 }
export const regimeLabel = (r: string) => ({ cheap: 'Below-median valuation', fair: 'Fair valuation', rich: 'Rich valuation' } as Record<string, string>)[r] ?? r
