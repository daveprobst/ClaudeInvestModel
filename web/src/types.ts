export type Metrics = {
  cagr: number; vol: number; sharpe: number | null; sortino: number | null; max_dd: number; ulcer: number
  calmar: number | null; up_capture: number; down_capture: number; worst_12m: number
  pct_positive_years: number; final_multiple: number; avg_equity: number
}
export type Period = { label: string; start: string; end: string; months: number; metrics: Record<'bulwark' | 'buyhold' | 'cash' | 'faber' | 'static', Metrics> }
export type Episode = {
  peak: string; trough: string; recovery: string | null; depth_bh: number
  bulwark_peak_to_trough: number; bulwark_max_dd: number; bulwark_full_cycle: number
  buyhold_peak_to_trough: number; buyhold_max_dd: number; buyhold_full_cycle: number
  faber_peak_to_trough: number; faber_max_dd: number; faber_full_cycle: number
  bulwark_equity_at_trough: number; months_peak_to_trough: number
}
export type Variant = { cagr: number; max_dd: number; sharpe: number; ulcer: number; calmar: number; up: number; down: number; avg_equity: number }
export type Snapshot = {
  asof: string; next_month: string; weight: number; regime: 'cheap' | 'fair' | 'rich'; n_flags: number; step: number
  flags: Record<'below_sma' | 'neg_mom' | 'curve_inv' | 'credit_stress' | 'sahm', boolean>
  price: number; sma: number; price_vs_sma: number; trip_sma: number; trip_sma_distance: number
  mom12: number; cash12: number; trip_mom_distance: number
  curve: number; credit_spread: number; credit_pct: number; sahm_gap: number | null
  cape: number; cape_pct: number; cape_shiller: number; buffett: number; buffett_pct: number; val_score: number
  live: { sp500?: number; sp500_date?: string; vix?: number; vix_date?: string; nfci?: number; nfci_date?: string }
  cape_median: number; buffett_median: number
}
export type Model = {
  name: string; generated: string; params: Record<string, number | string | boolean | string[]>
  flag_labels: Record<string, string>
  snapshot: Snapshot
  headline: Record<'full' | 'holdout' | 'since1990' | 'since2010' | 'lost_decades', Period>
  calendar: { year: number; bulwark: number; buyhold: number; cash: number; avg_equity: number }[]
  episodes: Episode[]
  rolling10: {
    years: number; windows: number; share_bulwark_ahead: number; share_within_1pt: number; median_diff: number; worst_diff: number; best_diff: number
    worst_bulwark: number; worst_buyhold: number; median_bulwark: number; median_buyhold: number; median_dd_bulwark: number; median_dd_buyhold: number
    series: { d: string; b: number; h: number }[]
  }
  flag_diagnostics: { period: string; flag: string; share_on: number; xs_on: number | null; xs_off: number | null }[]
  ablations: { name: string; full: Variant; holdout: Variant }[]
  sensitivity: {
    lookbacks: (Variant & { sma: number; mom: number; chosen: boolean })[]
    valuation: (Variant & { rich: number; cheap: number; chosen: boolean })[]
    steps: (Variant & { step: number; tilt: string; chosen: boolean })[]
    other: (Variant & { group: string; label: string; chosen: boolean })[]
  }
  bootstrap: {
    draws: number; block_months: number; cagr_diff_q: number[]; maxdd_diff_q: number[]; sharpe_diff_q: number[]
    p_sharpe_better: number; p_maxdd_better: number; p_cagr_within_1pt: number; p_cagr_better: number
  }
  international: { market: string; start: string; months: number; bh_cagr: number; bh_dd: number; trend_cagr: number; trend_dd: number; faber_cagr: number; faber_dd: number; equity_share: number }[]
  sources: { name: string; used_for: string; last: string; url: string }[]
  turnover_per_year: number; trades_per_year: number
  regime_share: Record<string, number>; flag_share: Record<string, number>
  audit: { passed: boolean | null; summary: string }
}
export type Series = {
  d: string[]; bulwark: number[]; buyhold: number[]; cash: number[]; faber: number[]
  w: (number | null)[]; wt: (number | null)[]; nf: number[]; flags: number[]; regime: number[]
  cape: (number | null)[]; buffett: (number | null)[]; cape_pct: (number | null)[]; buffett_pct: (number | null)[]
  price: (number | null)[]; sma: (number | null)[]; curve: (number | null)[]; credit: (number | null)[]; sahm: (number | null)[]
}

export type PerfSeries = Pick<Series, 'd' | 'bulwark' | 'buyhold' | 'cash' | 'faber' | 'w' | 'nf' | 'regime'>

export type RegionInput = { label: string; source: string; origin: 'native' | 'substitute' | 'assumption' }
export type RegionSnapshot = {
  asof: string; next_month: string; weight: number; regime: 'cheap' | 'fair' | 'rich'; n_flags: number; step: number
  flags: Record<'below_sma' | 'neg_mom' | 'curve_inv', boolean>
  price: number; sma: number; price_vs_sma: number; trip_sma: number; trip_sma_distance: number
  mom12: number; cash12: number; trip_mom_distance: number; curve: number; short_rate: number; long_yield: number
  us_cape: number; us_cape_pct: number; us_buffett: number; us_buffett_pct: number; val_score: number
}
export type RegionPayload = {
  id: string; name: string; currency: string; generated: string; first: string; dividend_yield: number
  inputs: RegionInput[]; snapshot: RegionSnapshot
  headline: Record<string, Period>
  calendar: Model['calendar']; episodes: Episode[]; rolling10: Model['rolling10']
  ablations: { name: string; full: Variant & { bh_cagr?: number } }[]
  bootstrap: Model['bootstrap']
  turnover_per_year: number; trades_per_year: number
  series: PerfSeries & { price: (number | null)[]; sma: (number | null)[]; curve: (number | null)[]; us_cape: (number | null)[]; us_buffett: (number | null)[]; wt: (number | null)[]; flags: number[] }
  access: { plan: 'demo' | 'premium'; demo: boolean }
  audit: { passed: boolean | null; summary: string }
}
