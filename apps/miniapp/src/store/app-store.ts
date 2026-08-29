import { create } from 'zustand'
import { storage } from '../services/storage'
import type { ReplayMode, ReplaySession, SessionSummary } from '../types/market'

interface TrainingPreferences {
  instrumentId: string
  timeframe: string
  mode: ReplayMode
  warmupBars: number
}

interface AppState {
  hydrated: boolean
  preferences: TrainingPreferences
  currentSession: ReplaySession | null
  localSessions: SessionSummary[]
  streak: number
  setPreferences: (patch: Partial<TrainingPreferences>) => void
  setCurrentSession: (session: ReplaySession | null) => void
  addLocalSession: (session: ReplaySession) => void
  hydrate: () => void
  resetLocalData: () => void
}

const defaults: TrainingPreferences = {
  instrumentId: 'SPY', timeframe: '5m', mode: 'hidden_answer', warmupBars: 12
}

export const useAppStore = create<AppState>((set, get) => ({
  hydrated: false,
  preferences: defaults,
  currentSession: null,
  localSessions: [],
  streak: 4,
  setPreferences: (patch) => {
    const preferences = { ...get().preferences, ...patch }
    storage.set('preferences', preferences)
    set({ preferences })
  },
  setCurrentSession: (currentSession) => {
    if (currentSession) storage.set('current-session', currentSession)
    else storage.remove('current-session')
    set({ currentSession })
  },
  addLocalSession: (session) => {
    const item: SessionSummary = {
      session_id: session.session_id,
      day: session.info.day,
      provider: session.info.provider,
      instrument_id: get().preferences.instrumentId,
      mode: session.info.mode,
      state: session.info.is_completed ? 'completed' : 'active',
      cursor_index: session.info.bar_index,
      judgment_count: 0,
      created_at: new Date().toISOString()
    }
    const localSessions = [item, ...get().localSessions.filter((value) => value.session_id !== item.session_id)].slice(0, 30)
    storage.set('sessions', localSessions)
    set({ localSessions })
  },
  hydrate: () => set({
    preferences: storage.get('preferences', defaults),
    currentSession: storage.get<ReplaySession | null>('current-session', null),
    localSessions: storage.get<SessionSummary[]>('sessions', []),
    streak: storage.get('streak', 4),
    hydrated: true
  }),
  resetLocalData: () => {
    storage.clear()
    set({ preferences: defaults, currentSession: null, localSessions: [], streak: 0 })
  }
}))
