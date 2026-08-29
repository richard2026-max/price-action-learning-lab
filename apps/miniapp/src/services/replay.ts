import { request } from './request'
import type { CreateSessionPayload, JudgmentPayload, ReplaySession, SessionSummary } from '../types/market'

export const replayService = {
  availableDays(instrumentId = 'SPY', provider = 'synthetic') {
    return request<{ days: string[] }>('/replay/days', { query: { instrument_id: instrumentId, provider } })
  },
  randomDay(seed: number, instrumentId = 'SPY', provider = 'synthetic') {
    return request<{ day: string }>('/replay/random-day', { query: { seed, instrument_id: instrumentId, provider } })
  },
  createSession(payload: CreateSessionPayload) {
    return request<ReplaySession>('/replay/sessions', { method: 'POST', data: payload })
  },
  getSession(sessionId: string, provider = 'synthetic', instrumentId = 'SPY') {
    return request<ReplaySession>(`/replay/sessions/${sessionId}`, { query: { provider, instrument_id: instrumentId } })
  },
  advance(sessionId: string, n: number, cursorVersion: number) {
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    return request<ReplaySession>(`/replay/sessions/${sessionId}/advance`, {
      method: 'POST',
      data: { n, expected_cursor_version: cursorVersion, request_id: requestId },
    })
  },
  back(sessionId: string) {
    return request<ReplaySession>(`/replay/sessions/${sessionId}/back`, { method: 'POST' })
  },
  submitJudgment(sessionId: string, payload: JudgmentPayload) {
    const clientRequestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    return request<{ id: number; bar_index: number; submitted_at: string }>(
      `/replay/sessions/${sessionId}/judgments`,
      { method: 'POST', data: { ...payload, client_request_id: clientRequestId } },
    )
  },
  listSessions(limit = 100) {
    return request<SessionSummary[]>('/replay/sessions', { query: { limit } })
  }
}
