import { Button, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useMemo, useState } from 'react'
import { CandlestickChart } from '../../components/candlestick-chart'
import { PredictForm } from '../../components/predict-form'
import { replayService } from '../../services/replay'
import { useAppStore } from '../../store/app-store'
import type { JudgmentPayload, ReplaySession } from '../../types/market'
import './index.scss'

export default function ReplayPage() {
  const stored = useAppStore((state) => state.currentSession)
  const setCurrentSession = useAppStore((state) => state.setCurrentSession)
  const addLocalSession = useAppStore((state) => state.addLocalSession)
  const [session, setSession] = useState<ReplaySession | null>(stored)
  const [showPredict, setShowPredict] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [judgmentLocked, setJudgmentLocked] = useState(Boolean(stored?.candidates?.length))
  const [advancing, setAdvancing] = useState(false)
  const last = session?.bars[session.bars.length - 1]
  const range = useMemo(() => last ? last.high - last.low : 0, [last])

  if (!session) {
    return <View className='screen replay-screen'>
      <View className='panel replay-empty'>
        <Text className='eyebrow'>NO ACTIVE SESSION</Text>
        <Text className='gate-title'>没有可恢复的训练会话</Text>
        <Button className='primary-button' onClick={() => Taro.switchTab({ url: '/pages/training/index' })}>返回训练台</Button>
      </View>
    </View>
  }

  const update = (next: ReplaySession) => {
    setSession(next)
    setCurrentSession(next)
    addLocalSession(next)
  }

  const submit = async (payload: JudgmentPayload) => {
    setSubmitting(true)
    try {
      await replayService.submitJudgment(session.session_id, payload)
      setJudgmentLocked(true)
      setShowPredict(false)
      Taro.showToast({ title: '判断已锁定', icon: 'success' })
    } catch (error) {
      Taro.showModal({
        title: '判断未提交',
        content: error instanceof Error ? error.message : '网络异常，请重试。',
        showCancel: false,
      })
    } finally {
      setSubmitting(false)
    }
  }

  const advance = async (n: number) => {
    setAdvancing(true)
    try {
      const next = await replayService.advance(session.session_id, n, session.info.cursor_version)
      update(next)
      setJudgmentLocked(false)
    } catch (error) {
      Taro.showModal({
        title: '游标未推进',
        content: error instanceof Error ? error.message : '服务端状态未改变，请重新加载会话。',
        confirmText: '重新加载',
        success: async (result) => {
          if (!result.confirm) return
          try {
            update(await replayService.getSession(session.session_id, session.info.provider))
          } catch {
            Taro.showToast({ title: '重新加载失败', icon: 'none' })
          }
        },
      })
    } finally {
      setAdvancing(false)
    }
  }

  const back = async () => {
    setAdvancing(true)
    try {
      update(await replayService.back(session.session_id))
      setJudgmentLocked(false)
    } catch (error) {
      Taro.showToast({ title: error instanceof Error ? error.message : '无法后退', icon: 'none' })
    } finally {
      setAdvancing(false)
    }
  }

  return <View className='screen replay-screen'>
    <View className='replay-top'>
      <View><Text className='eyebrow'>NO LOOKAHEAD / SERVER CURSOR</Text><Text className='replay-day mono'>{session.info.day}</Text></View>
      <View className='live-badge'><Text className='live-dot' /> BAR {session.info.bar_index + 1}</View>
    </View>

    <CandlestickChart bars={session.bars} ema20={session.ema20} keyLevels={session.key_levels} />

    <View className='tape-row'>
      <View><Text className='section-label'>O</Text><Text className='mono'>{last?.open.toFixed(2)}</Text></View>
      <View><Text className='section-label'>H</Text><Text className='mono up'>{last?.high.toFixed(2)}</Text></View>
      <View><Text className='section-label'>L</Text><Text className='mono down'>{last?.low.toFixed(2)}</Text></View>
      <View><Text className='section-label'>RANGE</Text><Text className='mono'>{range.toFixed(2)}</Text></View>
    </View>

    <View className={`discipline panel ${judgmentLocked ? 'locked' : ''}`}>
      <View><Text className='section-label'>DECISION GATE</Text><Text className='gate-title'>{judgmentLocked ? '判断已锁定，可推进' : '未来 K 线保持封锁'}</Text></View>
      <Text className='gate-code mono'>{judgmentLocked ? 'UNLOCKED' : 'PREDICT FIRST'}</Text>
    </View>

    {!judgmentLocked ? <Button className='primary-button decision-button' onClick={() => setShowPredict(true)}>记录此刻判断</Button> : <View className='advance-grid'>
      {session.info.mode === 'free' && <Button className='secondary-button' disabled={advancing} onClick={back}>−1 BAR</Button>}
      <Button className='secondary-button' loading={advancing} disabled={advancing} onClick={() => advance(1)}>+1 BAR</Button>
      <Button className='primary-button' loading={advancing} disabled={advancing} onClick={() => advance(5)}>+5 BARS</Button>
    </View>}
    <Text className='replay-footnote'>客户端不会缓存或推演未来价格。网络失败时服务端游标保持不变。</Text>
    {showPredict && <PredictForm submitting={submitting} onSubmit={submit} onCancel={() => setShowPredict(false)} />}
  </View>
}
