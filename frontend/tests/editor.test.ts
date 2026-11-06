import { afterEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { requestJson } from '../src/api/client'
import { toPlanInput, useDraftEditor } from '../src/modules/trips/useDraftEditor'
import type { PlanView } from '../src/types/contracts'
import { deferred, draft } from './fixtures'

vi.mock('../src/api/client', () => ({ requestJson: vi.fn() }))
const scopes: ReturnType<typeof effectScope>[] = []
function editor() {
  const scope = effectScope()
  scopes.push(scope)
  return scope.run(useDraftEditor)!
}
afterEach(() => { scopes.splice(0).forEach(scope => scope.stop()); vi.resetAllMocks() })

describe('草案版本和约定字段', () => {
  it('提交 ID 而非价格/状态，编辑不改变父组件草案', () => {
    const plan = draft()
    const before = JSON.stringify(plan)
    const state = editor()
    state.load(plan)
    state.remove(1, 'a')
    expect(JSON.stringify(plan)).toBe(before)
    expect(state.checked.value).toBeNull()
    expect(state.input.value!.days[0].note).toBeNull()
    expect(state.input.value!.days[1].note).toBe('第二天旧建议')
    expect(Object.keys(toPlanInput(plan)).sort()).toEqual(
      ['city', 'day_count', 'preferences', 'budget_cny', 'mode', 'days'].sort(),
    )
    expect(toPlanInput(plan).days[0].attraction_ids).toEqual(['a', 'b'])
  })

  it('移动清除来源与目标日说明，重排只清除当日说明', () => {
    const state = editor()
    state.load(draft())
    state.move(1, 2, 'a')
    expect(state.input.value!.days.map(day => day.note)).toEqual([null, null, '第三天保留建议'])
    expect(state.input.value!.days[1].attraction_ids).toEqual(['c', 'a'])
    state.load(draft())
    state.reorder(1, 1, -1)
    expect(state.input.value!.days[0].attraction_ids).toEqual(['b', 'a'])
    expect(state.input.value!.days[1].note).toBe('第二天旧建议')
    state.add(3, 'a')
    expect(state.input.value!.days[2].attraction_ids).toEqual([])
    state.add(3, 'd')
    expect(state.input.value!.days[2].attraction_ids).toEqual(['d'])
    state.move(3, 1, 'd')
    expect(state.input.value!.days[2].attraction_ids).toEqual(['d'])
  })

  it('重复点击校验只发一个请求，采用服务端费用和警告', async () => {
    const state = editor()
    state.load(draft())
    state.remove(1, 'a')
    const response = deferred<PlanView>()
    vi.mocked(requestJson).mockReturnValue(response.promise)
    const first = state.validate()
    await state.validate()
    expect(requestJson).toHaveBeenCalledTimes(1)
    const body = JSON.parse(vi.mocked(requestJson).mock.calls[0][1]!.body as string)
    expect(body.days[0]).toEqual({ day: 1, attraction_ids: ['b'], note: null })
    expect(body).not.toHaveProperty('total_cny')
    const server = { ...draft(), total_cny: 123, warnings: ['后端重算提示'] }
    response.resolve(server)
    await first
    expect(state.checked.value).toEqual(server)
  })

  it.each(['success', 'failure'] as const)('忽略编辑前的过期%s响应，且不结束新请求', async outcome => {
    const state = editor()
    state.load(draft())
    const old = deferred<PlanView>()
    const current = deferred<PlanView>()
    vi.mocked(requestJson).mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
    const oldRequest = state.validate()
    const oldSignal = vi.mocked(requestJson).mock.calls[0][1]!.signal
    state.remove(1, 'a')
    expect(oldSignal?.aborted).toBe(true)
    const newRequest = state.validate()
    if (outcome === 'success') old.resolve(draft())
    else old.reject(new Error('过期错误'))
    await oldRequest
    expect(state.checked.value).toBeNull()
    expect(state.error.value).toBe('')
    expect(state.validating.value).toBe(true)
    current.resolve(draft())
    await newRequest
    expect(state.validating.value).toBe(false)
    expect(state.checked.value).not.toBeNull()
  })

  it('新草案和卸载使旧请求失效，业务错误不会显示校验成功', async () => {
    const state = editor()
    state.load(draft())
    const old = deferred<PlanView>()
    vi.mocked(requestJson).mockReturnValueOnce(old.promise)
    const request = state.validate()
    state.load(null)
    old.resolve(draft())
    await request
    expect(state.checked.value).toBeNull()
    expect(state.hasUnsavedChanges.value).toBe(false)
    state.load(draft())
    vi.mocked(requestJson).mockRejectedValueOnce(new Error('南澳与市区不能安排在同一天。'))
    await state.validate()
    expect(state.checked.value).toBeNull()
    expect(state.error.value).toContain('南澳')
  })

  it('预算本地校验拒绝空值、小数、负数，修改说明也使结果失效', async () => {
    const state = editor()
    state.load(draft())
    for (const value of [NaN, -1, 1.5]) {
      state.setBudget(value)
      await state.validate()
      expect(state.error.value).toContain('非负整数')
    }
    expect(requestJson).not.toHaveBeenCalled()
    state.load(draft())
    state.setNote(1, '新的用户安排')
    expect(state.checked.value).toBeNull()
    expect(state.input.value!.days[0].note).toBe('新的用户安排')
  })
})
