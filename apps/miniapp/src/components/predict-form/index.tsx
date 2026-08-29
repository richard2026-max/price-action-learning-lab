import { Button, Input, ScrollView, Text, Textarea, View } from '@tarojs/components'
import { firstJudgmentErrorMessage, validateJudgment } from '@price-action/domain'
import { useMemo, useState } from 'react'
import type { ContextLabel, Direction, Grade, JudgmentPayload, Ternary } from '../../types/market'
import './index.scss'

interface Props {
  onSubmit: (payload: JudgmentPayload) => Promise<void> | void
  onCancel: () => void
  submitting?: boolean
}

const initial: JudgmentPayload = {
  context_label: 'trading_range', structure_note: '', pullback_present: 'unknown', bar_counting_note: '',
  considering_trade: false, direction: 'none', reasons: ['', ''], entry: null, stop: null, target: null,
  probability_estimate: 'okay', confidence: 'okay'
}

export function PredictForm({ onSubmit, onCancel, submitting = false }: Props) {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<JudgmentPayload>(initial)
  const steps = ['环境', '结构', '计划', '校准']
  const error = useMemo(() => validate(form, step), [form, step])
  const patch = (value: Partial<JudgmentPayload>) => setForm((current) => ({ ...current, ...value }))

  const next = async () => {
    if (error) return
    if (step < steps.length - 1) setStep(step + 1)
    else await onSubmit({ ...form, reasons: form.reasons.filter((reason) => reason.trim()) })
  }

  return (
    <View className='predict-mask'>
      <View className='predict-sheet'>
        <View className='predict-header'>
          <View>
            <Text className='eyebrow'>PREDICT FIRST</Text>
            <Text className='predict-title'>先判断，再看答案</Text>
          </View>
          <Text className='close' onClick={onCancel}>×</Text>
        </View>
        <View className='step-track'>
          {steps.map((label, index) => <View key={label} className={`step ${index <= step ? 'active' : ''}`}><Text>{String(index + 1).padStart(2, '0')}</Text><Text>{label}</Text></View>)}
        </View>
        <ScrollView scrollY className='predict-body'>
          {step === 0 && <>
            <Field label='01 / 当前市场环境'>
              <Chips value={form.context_label} options={[
                ['trend_up', '上涨趋势'], ['trend_down', '下跌趋势'], ['trading_range', '交易区间'], ['transition', '转折过渡']
              ]} onChange={(value) => patch({ context_label: value as ContextLabel })} />
            </Field>
            <Field label='02 / 是否存在回调'>
              <Chips value={form.pullback_present} options={[[ 'yes', '有' ], [ 'no', '无' ], [ 'unknown', '不确定' ]]} onChange={(value) => patch({ pullback_present: value as Ternary })} />
            </Field>
          </>}
          {step === 1 && <>
            <Field label='03 / 结构依据'>
              <Textarea className='terminal-input textarea' maxlength={240} placeholder='高低点、突破、测试、区间边界…' value={form.structure_note} onInput={(event) => patch({ structure_note: event.detail.value })} />
            </Field>
            <Field label='04 / Bar counting'>
              <Textarea className='terminal-input textarea short' maxlength={160} placeholder='第几次推动？是否出现楔形或二次入场？' value={form.bar_counting_note} onInput={(event) => patch({ bar_counting_note: event.detail.value })} />
            </Field>
          </>}
          {step === 2 && <>
            <Field label='05 / 此刻考虑交易吗'>
              <Chips value={form.considering_trade ? 'yes' : 'no'} options={[[ 'no', '观察 / 不交易' ], [ 'yes', '制定交易计划' ]]} onChange={(value) => patch({ considering_trade: value === 'yes', direction: value === 'yes' ? 'long' : 'none' })} />
            </Field>
            {form.considering_trade && <>
              <Field label='06 / 方向'>
                <Chips value={form.direction} options={[[ 'long', 'LONG 做多' ], [ 'short', 'SHORT 做空' ]]} onChange={(value) => patch({ direction: value as Direction })} />
              </Field>
              <Field label='07 / 两个独立理由'>
                <Input className='terminal-input' placeholder='理由 A' value={form.reasons[0]} onInput={(event) => patch({ reasons: [event.detail.value, form.reasons[1]] })} />
                <Input className='terminal-input reason-second' placeholder='理由 B' value={form.reasons[1]} onInput={(event) => patch({ reasons: [form.reasons[0], event.detail.value] })} />
              </Field>
              <Field label='08 / 价格计划'>
                <View className='price-grid'>
                  <PriceInput label='ENTRY' value={form.entry} onChange={(entry) => patch({ entry })} />
                  <PriceInput label='STOP / 失效点' value={form.stop} onChange={(stop) => patch({ stop })} />
                  <PriceInput label='TARGET' value={form.target} onChange={(target) => patch({ target })} />
                </View>
              </Field>
            </>}
          </>}
          {step === 3 && <>
            <Field label='09 / 机会质量'>
              <GradeChips value={form.probability_estimate} onChange={(probability_estimate) => patch({ probability_estimate })} />
            </Field>
            <Field label='10 / 你的置信度'>
              <GradeChips value={form.confidence} onChange={(confidence) => patch({ confidence })} />
            </Field>
            <View className='lock-note'><Text className='lock-mark'>LOCK</Text><Text>提交后判断将锁定。后续 K 线不能改写此刻的认知。</Text></View>
          </>}
        </ScrollView>
        <View className='form-error'>{error || ' '}</View>
        <View className='predict-actions'>
          {step > 0 && <Button className='secondary-button back-button' onClick={() => setStep(step - 1)}>上一步</Button>}
          <Button className='primary-button next-button' disabled={Boolean(error) || submitting} loading={submitting} onClick={next}>{step === 3 ? '锁定判断' : '继续'}</Button>
        </View>
      </View>
    </View>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <View className='field'><Text className='field-label'>{label}</Text>{children}</View>
}

function Chips({ value, options, onChange }: { value: string; options: string[][]; onChange: (value: string) => void }) {
  return <View className='chips'>{options.map(([key, label]) => <View key={key} className={`chip ${value === key ? 'selected' : ''}`} onClick={() => onChange(key)}>{label}</View>)}</View>
}

function GradeChips({ value, onChange }: { value: Grade; onChange: (value: Grade) => void }) {
  return <Chips value={value} options={[[ 'good', 'GOOD / 优势' ], [ 'okay', 'OKAY / 一般' ], [ 'bad', 'BAD / 较差' ]]} onChange={(next) => onChange(next as Grade)} />
}

function PriceInput({ label, value, onChange }: { label: string; value: number | null; onChange: (value: number | null) => void }) {
  return <View className='price-input'><Text>{label}</Text><Input className='terminal-input mono' type='digit' value={value === null ? '' : String(value)} placeholder='0.00' onInput={(event) => { const next = Number(event.detail.value); onChange(event.detail.value === '' || Number.isNaN(next) ? null : next) }} /></View>
}

function validate(form: JudgmentPayload, step: number): string {
  if (step === 1 && !form.structure_note.trim()) return '请写下可复盘的结构依据'
  if (step !== 2) return ''
  return firstJudgmentErrorMessage(validateJudgment(form))
}
