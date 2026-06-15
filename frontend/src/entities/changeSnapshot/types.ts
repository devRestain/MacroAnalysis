export interface ChangeSnapshot {
  key: string
  label: string
  category: string
  value: number | null
  unit: string | null
  delta1d: number | null
  delta1dPct: number | null
  delta1wPct: number | null
  delta1mPct: number | null
  delta3mPct: number | null
  zScore1y: number | null
  direction: 'up' | 'down' | 'flat' | 'unknown'
  signal: 'green' | 'yellow' | 'red' | string
  date: string | null
}

