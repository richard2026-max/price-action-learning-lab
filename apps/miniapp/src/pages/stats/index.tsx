import { Text, View } from '@tarojs/components'
import { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import { analyticsService } from '../../services/analytics'
import type { AnalyticsOverview } from '../../types/analytics'
import './index.scss'

const fallback: AnalyticsOverview = {
  behavior: { total_sessions: 0, completed_sessions: 0, total_judgments: 0, total_annotations: 0, total_reviewed_candidates: 0, total_confirmed_positives: 0, total_rejected_negatives: 0, total_favorites: 0, total_mistakes: 0 },
  judgment: { context_breakdown: { trend_up: 0, trend_down: 0, trading_range: 0, transition: 0 }, trade_decision_breakdown: { trade: 0, pass: 0 }, confidence_breakdown: { good: 0, okay: 0, bad: 0 }, probability_breakdown: { good: 0, okay: 0, bad: 0 } },
  rejections: { reason_counts: {} }, recent_mistakes: [], recent_favorites: []
}

export default function StatsPage() {
  const [data, setData] = useState(fallback)
  useDidShow(() => { analyticsService.overview().then(setData).catch(() => undefined) })
  const contexts = data.judgment.context_breakdown
  const max = Math.max(1, ...Object.values(contexts))
  const completion = data.behavior.total_sessions ? Math.round(data.behavior.completed_sessions / data.behavior.total_sessions * 100) : 0

  return <View className='screen stats-screen'>
    <Text className='eyebrow'>LEARNING TELEMETRY</Text>
    <Text className='page-title'>过程统计</Text>
    <Text className='page-subtitle'>追踪训练密度与判断校准，不奖励短期随机结果。</Text>
    <View className='stats-hero panel'>
      <View><Text className='section-label'>判断样本</Text><Text className='big-number mono'>{data.behavior.total_judgments}</Text></View>
      <View className='completion-ring'><Text className='mono'>{completion}%</Text><Text>完成率</Text></View>
    </View>
    <View className='metric-grid'>
      <Metric label='训练会话' value={data.behavior.total_sessions} unit='SESSIONS' />
      <Metric label='复盘标注' value={data.behavior.total_annotations} unit='NOTES' />
      <Metric label='已审证据' value={data.behavior.total_reviewed_candidates} unit='CASES' />
      <Metric label='错题库存' value={data.behavior.total_mistakes} unit='ERRORS' danger />
    </View>
    <View className='distribution panel'>
      <Text className='section-label'>环境判断分布 / CONTEXT</Text>
      {Object.entries(contexts).map(([key, value]) => <View className='bar-row' key={key}>
        <Text className='bar-name'>{labelOf(key)}</Text><View className='bar-track'><View className='bar-fill' style={{ width: `${value / max * 100}%` }} /></View><Text className='bar-value mono'>{value}</Text>
      </View>)}
    </View>
    <View className='calibration-note'><Text className='mono'>NEXT SIGNAL</Text><Text>“OKAY” 档判断占比最高。下一阶段重点：区分一般机会与可放弃机会。</Text></View>
  </View>
}

function Metric({ label, value, unit, danger = false }: { label: string; value: number; unit: string; danger?: boolean }) {
  return <View className='metric-card'><Text className='section-label'>{label}</Text><Text className={`metric-number mono ${danger ? 'down' : ''}`}>{value}</Text><Text className='metric-caption'>{unit}</Text></View>
}
function labelOf(key: string) { return ({ trend_up: '上涨趋势', trend_down: '下跌趋势', trading_range: '交易区间', transition: '转折过渡' } as Record<string, string>)[key] || key }
