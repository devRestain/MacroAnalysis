import { getFomcOverview } from './calendar'
import { getTypedAiSummary } from './ai'

export async function getCommunicationOverview() {
  const [fomc, powellSummary] = await Promise.all([
    getFomcOverview(),
    getTypedAiSummary('communication', { targetKey: 'Powell', days: 30 }),
  ])
  return { fomc, powellSummary }
}

