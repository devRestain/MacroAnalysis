export interface OpsStatus {
  frontendStatus: 'ready'
  apiHealth?: Record<string, unknown> | null
  dashboardUpdatedAt?: string | null
  aiAvailable?: boolean | null
  sentimentAvailable?: boolean | null
}

