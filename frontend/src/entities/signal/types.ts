export type SignalDirection = 'up' | 'down' | 'flat' | 'unknown'

export interface Signal {
  indicatorKey?: string
  signalType?: string
  direction?: SignalDirection
  strength?: number | null
  generatedAt?: string | null
}

