import { request } from './request'
import type { AnalyticsOverview } from '../types/analytics'

export const analyticsService = {
  overview() {
    return request<AnalyticsOverview>('/analytics/overview')
  }
}
