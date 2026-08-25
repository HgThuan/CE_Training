import { http } from '@/shared/lib/http'

export type RecommendationSource = 'home' | 'product' | 'similar' | 'search'

interface Attribution {
  recommendation_id: string
  product_id: string
  source: RecommendationSource
  position: number
  recorded_at: number
}

const VISITOR_KEY = 'mercato.recommendation.visitor'
const ATTRIBUTION_PREFIX = 'mercato.recommendation.attribution:'
const recordedImpressions = new Set<string>()

function visitorId(): string {
  const value = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
  try {
    const stored = window.localStorage.getItem(VISITOR_KEY)
    if (stored) return stored
    window.localStorage.setItem(VISITOR_KEY, value)
  } catch {
    // Recommendation telemetry is optional and must never block shopping.
  }
  return value
}

function sendEvent(attribution: Attribution, eventType: 'impression' | 'click' | 'add_to_cart') {
  return http.post('/ai/recommendation-events/', {
    ...attribution,
    event_type: eventType,
    visitor_id: visitorId(),
  })
}

export function trackRecommendationImpression(
  recommendationId: string,
  productId: string,
  source: RecommendationSource,
  position: number,
): void {
  if (!recommendationId) return
  const impressionKey = `${recommendationId}:${productId}:${source}`
  if (recordedImpressions.has(impressionKey)) return
  recordedImpressions.add(impressionKey)

  void sendEvent(
    {
      recommendation_id: recommendationId,
      product_id: productId,
      source,
      position,
      recorded_at: Date.now(),
    },
    'impression',
  ).catch(() => undefined)
}

export function trackRecommendationClick(
  recommendationId: string,
  productId: string,
  source: RecommendationSource,
  position: number,
): void {
  if (!recommendationId) return
  const attribution: Attribution = {
    recommendation_id: recommendationId,
    product_id: productId,
    source,
    position,
    recorded_at: Date.now(),
  }
  try {
    window.localStorage.setItem(`${ATTRIBUTION_PREFIX}${productId}`, JSON.stringify(attribution))
  } catch {
    // Attribution storage is optional; the click signal can still be recorded.
  }
  void sendEvent(attribution, 'click').catch(() => undefined)
}

export function trackRecommendationAddToCart(productId: string): void {
  const key = `${ATTRIBUTION_PREFIX}${productId}`
  let raw: string | null = null
  try {
    raw = window.localStorage.getItem(key)
  } catch {
    return
  }
  if (!raw) return
  try {
    const attribution = JSON.parse(raw) as Attribution
    if (Date.now() - attribution.recorded_at > 30 * 24 * 60 * 60 * 1_000) {
      window.localStorage.removeItem(key)
      return
    }
    void sendEvent(attribution, 'add_to_cart').catch(() => undefined)
  } catch {
    window.localStorage.removeItem(key)
  }
}
