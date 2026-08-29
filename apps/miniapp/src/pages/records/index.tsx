import { Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import { replayService } from '../../services/replay'
import { useAppStore } from '../../store/app-store'
import type { SessionSummary } from '../../types/market'
import './index.scss'

export default function RecordsPage() {
  const localSessions = useAppStore((state) => state.localSessions)
  const setCurrentSession = useAppStore((state) => state.setCurrentSession)
  const [sessions, setSessions] = useState<SessionSummary[]>(localSessions)
  useDidShow(() => {
    replayService.listSessions(50).then(setSessions).catch(() => setSessions(localSessions))
  })

  return <View className='screen records-screen'>
    <Text className='eyebrow'>DECISION LEDGER</Text>
    <Text className='page-title'>训练记录</Text>
    <Text className='page-subtitle'>不是盈亏账本，是当时判断的时间切片。</Text>
    <View className='ledger-head mono'><Text>DATE / SYMBOL</Text><Text>CURSOR</Text><Text>STATE</Text></View>
    <View className='ledger-list'>
      {sessions.length === 0 && <View className='empty panel'><Text className='empty-code mono'>NO RECORDS</Text><Text>完成第一次 Predict First 后，记录会出现在这里。</Text></View>}
      {sessions.map((item, index) => <View className='ledger-row' key={item.session_id} onClick={async () => {
        Taro.showLoading({ title: '恢复会话' })
        try {
          const session = await replayService.getSession(item.session_id, item.provider, item.instrument_id)
          setCurrentSession(session)
          await Taro.navigateTo({ url: '/pages/replay/index' })
        } catch (error) {
          Taro.showToast({ title: error instanceof Error ? error.message : '恢复失败', icon: 'none' })
        } finally {
          Taro.hideLoading()
        }
      }}>
        <Text className='row-index mono'>{String(index + 1).padStart(2, '0')}</Text>
        <View className='row-main'><Text className='row-date mono'>{item.day}</Text><Text className='row-meta'>{item.instrument_id} · {item.mode.replace('_', ' ').toUpperCase()} · {item.judgment_count} 判断</Text></View>
        <Text className='row-cursor mono'>B{item.cursor_index + 1}</Text>
        <Text className={`row-state ${item.state === 'completed' ? 'done' : ''}`}>{item.state === 'completed' ? 'DONE' : 'OPEN'}</Text>
      </View>)}
    </View>
  </View>
}
