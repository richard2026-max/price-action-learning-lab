import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { useAppStore } from '../../store/app-store'
import { authService } from '../../services/auth'
import { replayService } from '../../services/replay'
import type { ReplayMode } from '../../types/market'
import './index.scss'

const modes: Array<{ key: ReplayMode; code: string; title: string; desc: string }> = [
  { key: 'hidden_answer', code: 'BLIND', title: '盲测训练', desc: '严格截断未来，判断后解锁证据' },
  { key: 'free', code: 'DRILL', title: '自由回放', desc: '按自己的节奏推进与回看' },
  { key: 'exam', code: 'SEALED', title: '封存考试', desc: '独立样本，只用于阶段评估' }
]

export default function TrainingPage() {
  const { preferences, setPreferences, setCurrentSession, addLocalSession, currentSession, streak } = useAppStore()
  const [loading, setLoading] = useState(false)

  const start = async () => {
    setLoading(true)
    try {
      await authService.ensureAuthenticated()
      const { day } = await replayService.randomDay(Date.now() % 2147483647, preferences.instrumentId)
      const session = await replayService.createSession({
        instrument_id: preferences.instrumentId, provider: 'synthetic', day,
        timeframe: preferences.timeframe, mode: preferences.mode, warmup_bars: preferences.warmupBars, context_days: 1
      })
      setCurrentSession(session)
      addLocalSession(session)
      await Taro.navigateTo({ url: '/pages/replay/index' })
    } catch (error) {
      Taro.showModal({
        title: '无法建立训练会话',
        content: error instanceof Error ? error.message : '请检查 API、网络和登录配置后重试。',
        showCancel: false,
      })
    } finally {
      setLoading(false)
    }
  }

  return <View className='screen training-screen'>
    <View className='topline'><Text className='eyebrow'>PA / TRAINING DESK</Text><Text className='status-dot'>SYSTEM READY</Text></View>
    <View className='hero'>
      <Text className='page-title'>读价格，{`\n`}不猜答案。</Text>
      <Text className='page-subtitle'>每一根 K 线出现前，先留下可审计的判断。训练认知过程，而不是结果记忆。</Text>
    </View>

    <View className='pulse panel'>
      <View><Text className='section-label'>CURRENT STREAK</Text><View><Text className='metric-value acid'>{streak}</Text><Text className='metric-unit'>DAYS</Text></View></View>
      <View className='pulse-divider' />
      <View><Text className='section-label'>PROTOCOL</Text><Text className='protocol'>PREDICT → REVEAL → REVIEW</Text></View>
    </View>

    <View className='section-head'><Text>选择训练协议</Text><Text className='mono muted'>01 / 03</Text></View>
    <View className='mode-list'>
      {modes.map((mode) => <View key={mode.key} className={`mode-card ${preferences.mode === mode.key ? 'selected' : ''}`} onClick={() => setPreferences({ mode: mode.key })}>
        <Text className='mode-code mono'>{mode.code}</Text>
        <View className='mode-copy'><Text className='mode-title'>{mode.title}</Text><Text className='mode-desc'>{mode.desc}</Text></View>
        <Text className='mode-check'>{preferences.mode === mode.key ? '●' : '○'}</Text>
      </View>)}
    </View>

    <View className='setup-grid panel'>
      <View><Text className='section-label'>标的</Text><Text className='setup-value mono'>{preferences.instrumentId}</Text></View>
      <View><Text className='section-label'>周期</Text><Text className='setup-value mono'>{preferences.timeframe.toUpperCase()}</Text></View>
      <View><Text className='section-label'>热身</Text><Text className='setup-value mono'>{preferences.warmupBars} BARS</Text></View>
    </View>

    <Button className='primary-button launch' loading={loading} disabled={loading} onClick={start}>{loading ? '建立无前视会话…' : '开始随机训练  ↗'}</Button>
    {currentSession && <View className='resume' onClick={() => Taro.navigateTo({ url: '/pages/replay/index' })}><Text>继续上次会话</Text><Text className='mono'>{currentSession.info.day} / BAR {currentSession.info.bar_index + 1} →</Text></View>}
  </View>
}
