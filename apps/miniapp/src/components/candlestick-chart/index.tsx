import { Canvas, View, Text } from '@tarojs/components'
import { calculatePriceRange, keyLevelPrices } from '@price-action/chart-core'
import Taro from '@tarojs/taro'
import { useEffect, useMemo, useRef } from 'react'
import type { KeyLevels, MarketBar } from '../../types/market'
import './index.scss'

interface Props {
  bars: MarketBar[]
  ema20?: Array<number | null>
  keyLevels?: KeyLevels
  height?: number
}

let chartSequence = 0

export function CandlestickChart({ bars, ema20 = [], keyLevels, height = 470 }: Props) {
  const idRef = useRef(`kline-${++chartSequence}`)
  const visibleBars = useMemo(() => bars.slice(-64), [bars])
  const last = visibleBars[visibleBars.length - 1]
  const change = last && visibleBars[0] ? last.close - visibleBars[0].open : 0

  useEffect(() => {
    if (!visibleBars.length) return
    const timer = setTimeout(() => {
      Taro.createSelectorQuery().select(`#${idRef.current}`).fields({ node: true, size: true }).exec((result) => {
        const item = result?.[0] as { node?: any; width?: number; height?: number } | undefined
        if (!item?.node || !item.width || !item.height) return
        const canvas = item.node
        const dpr = Taro.getWindowInfo().pixelRatio || 1
        canvas.width = item.width * dpr
        canvas.height = item.height * dpr
        const ctx = canvas.getContext('2d')
        ctx.scale(dpr, dpr)
        drawChart(ctx, item.width, item.height, visibleBars, ema20.slice(-visibleBars.length), keyLevels)
      })
    }, 40)
    return () => clearTimeout(timer)
  }, [visibleBars, ema20, keyLevels])

  return (
    <View className='chart-shell panel'>
      <View className='chart-head'>
        <View>
          <Text className='symbol'>SPY</Text>
          <Text className='timeframe mono'> · 5M / RTH</Text>
        </View>
        <View className='quote'>
          <Text className='mono'>{last?.close.toFixed(2) ?? '—'}</Text>
          <Text className={change >= 0 ? 'up quote-change' : 'down quote-change'}>{change >= 0 ? '+' : ''}{change.toFixed(2)}</Text>
        </View>
      </View>
      <Canvas id={idRef.current} type='2d' className='kline-canvas' style={{ height: `${height}rpx` }} />
      <View className='chart-legend'>
        <Text><Text className='legend-line ema' /> EMA20</Text>
        <Text><Text className='legend-line pdh' /> PDH / PDL</Text>
        <Text className='mono'>{visibleBars.length} BARS</Text>
      </View>
    </View>
  )
}

function drawChart(ctx: any, width: number, height: number, bars: MarketBar[], ema: Array<number | null>, levels?: KeyLevels) {
  const pad = { top: 12, right: 52, bottom: 24, left: 8 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom
  const range = calculatePriceRange(bars, {
    paddingRatio: 0.1,
    minimumSpan: 0.5,
    extraPrices: keyLevelPrices(levels),
  })
  if (!range) return
  const { min, max } = range
  const y = (value: number) => pad.top + ((max - value) / (max - min)) * plotH

  ctx.clearRect(0, 0, width, height)
  ctx.strokeStyle = '#202a34'
  ctx.lineWidth = 1
  ctx.setLineDash([2, 5])
  ctx.font = '9px Consolas'
  ctx.fillStyle = '#66717e'
  for (let i = 0; i <= 4; i++) {
    const gy = pad.top + plotH * i / 4
    ctx.beginPath(); ctx.moveTo(pad.left, gy); ctx.lineTo(width - pad.right, gy); ctx.stroke()
    const price = max - (max - min) * i / 4
    ctx.fillText(price.toFixed(2), width - pad.right + 6, gy + 3)
  }

  const namedLevels: Array<[string, number | null | undefined, string]> = [
    ['PDH', levels?.prev_day_high, '#ffbd4a'], ['PDL', levels?.prev_day_low, '#ffbd4a'], ['PDC', levels?.prev_day_close, '#607080']
  ]
  namedLevels.forEach(([label, value, color]) => {
    if (typeof value !== 'number' || value < min || value > max) return
    const ly = y(value)
    ctx.strokeStyle = color; ctx.setLineDash([5, 4]); ctx.beginPath(); ctx.moveTo(pad.left, ly); ctx.lineTo(width - pad.right, ly); ctx.stroke()
    ctx.fillStyle = color; ctx.fillText(label, pad.left + 3, ly - 3)
  })

  const slot = plotW / bars.length
  const bodyW = Math.max(2, Math.min(7, slot * .58))
  ctx.setLineDash([])
  bars.forEach((bar, index) => {
    const x = pad.left + slot * (index + .5)
    const rising = bar.close >= bar.open
    const color = rising ? '#41e2a0' : '#ff5f6d'
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(x, y(bar.high)); ctx.lineTo(x, y(bar.low)); ctx.stroke()
    const top = y(Math.max(bar.open, bar.close)); const bottom = y(Math.min(bar.open, bar.close))
    ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(1.4, bottom - top))
  })

  ctx.strokeStyle = '#55d8ff'; ctx.lineWidth = 1.35; ctx.beginPath()
  let started = false
  ema.forEach((value, index) => {
    if (value === null || value === undefined) return
    const x = pad.left + slot * (index + .5)
    if (!started) { ctx.moveTo(x, y(value)); started = true } else ctx.lineTo(x, y(value))
  })
  ctx.stroke()

  ctx.fillStyle = '#66717e'
  const labels = [0, Math.floor((bars.length - 1) / 2), bars.length - 1]
  labels.forEach((index) => {
    const date = new Date(bars[index].ts_close_utc)
    const label = `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}`
    const x = pad.left + slot * (index + .5)
    ctx.fillText(label, Math.min(x - 13, width - pad.right - 28), height - 6)
  })
}
