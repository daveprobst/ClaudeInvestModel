import { useEffect, useState } from 'react'
import type { Model, Series } from './types'

const base = import.meta.env.BASE_URL

export function useData() {
  const [state, setState] = useState<{ model: Model; series: Series } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    Promise.all([
      fetch(`${base}data/model.json`).then((r) => r.json() as Promise<Model>),
      fetch(`${base}data/series.json`).then((r) => r.json() as Promise<Series>),
    ])
      .then(([model, series]) => alive && setState({ model, series }))
      .catch((e) => alive && setError(String(e)))
    return () => { alive = false }
  }, [])
  return { data: state, error }
}
