import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../src/App.vue'
import TripWorkspace from '../src/modules/trips/TripWorkspace.vue'
import PlanningPanel from '../src/modules/planning/PlanningPanel.vue'
import { requestJson } from '../src/api/client'
import type { PlanView, SavedTrip } from '../src/types/contracts'
import { attraction, deferred, draft } from './fixtures'

vi.mock('../src/api/client', () => ({ requestJson: vi.fn() }))
const wrappers: ReturnType<typeof mount>[] = []
beforeEach(() => vi.mocked(requestJson).mockResolvedValue({ items: [] }))
afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.mocked(requestJson).mockReset()
  vi.restoreAllMocks()
})

it('未知票价和 null 预算状态不会显示为免费或预算满足，编辑隐藏旧总价', async () => {
  const plan = draft()
  plan.days[0].note = '<img src=x onerror=alert(1)>'
  const wrapper = mount(TripWorkspace, { props: { draft: plan, attractions: [] } })
  wrappers.push(wrapper)
  expect(wrapper.text()).toContain('门票待确认')
  expect(wrapper.text()).toContain('预算待确认')
  expect(wrapper.find('img').exists()).toBe(false)
  expect(wrapper.find('textarea').element.value).toContain('<img')
  await wrapper.get('button[aria-label="移除a"]').trigger('click')
  expect(wrapper.text()).toContain('待校验')
  expect(wrapper.find('.total').exists()).toBe(false)
  expect(wrapper.find('textarea').element.value).toBe('')
})

it('接入 B 组件事件；新草案需要确认，取消保留本地修改', async () => {
  const wrapper = mount(App, {
    global: { stubs: {
      PlanningPanel: { template: '<div />' },
      ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue" role="dialog"><slot /><slot name="footer" /></div>' },
    } },
  })
  wrappers.push(wrapper)
  wrapper.findComponent(PlanningPanel).vm.$emit('plan-generated', draft())
  await nextTick()
  await wrapper.get('button[aria-label="移除a"]').trigger('click')
  const another = { ...draft(), budget_cny: 90 }
  wrapper.findComponent(PlanningPanel).vm.$emit('plan-generated', another)
  await nextTick()
  expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  await wrapper.get('[role="dialog"] button').trigger('click')
  expect(wrapper.get('input[aria-label="草案门票预算"]').element).toHaveProperty('value', '50')
  expect(wrapper.find('button[aria-label="移除a"]').exists()).toBe(false)
  wrapper.findComponent(PlanningPanel).vm.$emit('plan-generated', another)
  await nextTick()
  const buttons = wrapper.findAll('[role="dialog"] button')
  await buttons[1].trigger('click')
  expect(wrapper.get('input[aria-label="草案门票预算"]').element).toHaveProperty('value', '90')
  expect(wrapper.find('button[aria-label="移除a"]').exists()).toBe(true)
})

it('确认后才保存当前已校验草案，随后可读取及删除快照', async () => {
  const plan = draft()
  const saved: SavedTrip = {
    ...plan, status: 'saved', trip_id: '67f49311-8552-4abc-8087-6f1158cb8efd',
    created_at: '2026-11-12T10:00:00+00:00',
  }
  let history: SavedTrip[] = []
  vi.mocked(requestJson).mockImplementation(async (path, init) => {
    if (init?.method === 'POST') {
      if (path === '/api/plans/validate') return plan
      expect(JSON.parse(String(init.body)).days[0].note).toBe('保存说明')
      history = [saved]
      return saved
    }
    if (path === '/api/trips') return { items: history }
    if (init?.method === 'DELETE') {
      history = []
      return
    }
    return saved
  })
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  const wrapper = mount(TripWorkspace, { props: { draft: plan, attractions: [] } })
  wrappers.push(wrapper)
  const button = (label: string) => wrapper.findAll('button').find(item => item.text() === label)!
  await flushPromises()
  await button('确认保存行程').trigger('click')
  expect(vi.mocked(requestJson)).not.toHaveBeenCalledWith('/api/trips', expect.anything())
  await wrapper.get('textarea').setValue('保存说明')
  expect(button('确认保存行程').attributes('disabled')).toBeDefined()
  await button('重新校验行程').trigger('click')
  await flushPromises()
  confirm.mockReturnValue(true)
  await button('确认保存行程').trigger('click')
  await flushPromises()
  expect(wrapper.text()).toContain('已保存')
  await button('查看详情').trigger('click')
  await flushPromises()
  expect(wrapper.find('[aria-label="历史行程详情"]').exists()).toBe(true)
  confirm.mockReturnValue(false)
  await button('删除行程').trigger('click')
  expect(history).toEqual([saved])
  confirm.mockReturnValue(true)
  await button('删除行程').trigger('click')
  await flushPromises()
  expect(wrapper.text()).toContain('已删除行程')
  expect(wrapper.find('[aria-label="历史行程详情"]').exists()).toBe(false)
  expect(wrapper.text()).toContain('还没有行程草案')
})

it('取消放弃保留草案，确认放弃会取消校验且允许直接接收下一份草案', async () => {
  const pending = deferred<PlanView>()
  vi.mocked(requestJson).mockImplementation(async (path) =>
    path === '/api/plans/validate' ? pending.promise : { items: [] },
  )
  const wrapper = mount(App, { global: { stubs: {
    PlanningPanel: { template: '<div />' },
    ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue" role="dialog" />' },
  } } })
  wrappers.push(wrapper)
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  const planning = wrapper.findComponent(PlanningPanel)
  planning.vm.$emit('plan-generated', draft())
  await nextTick()
  await wrapper.get('textarea').setValue('未保存的修改')
  const button = (label: string) => wrapper.findAll('button').find(item => item.text() === label)!
  await button('重新校验行程').trigger('click')
  const validation = vi.mocked(requestJson).mock.calls.find(([path]) => path === '/api/plans/validate')
  const signal = validation?.[1]?.signal
  await button('放弃草案').trigger('click')
  expect(wrapper.get('textarea').element.value).toBe('未保存的修改')
  expect(signal?.aborted).toBe(false)

  confirm.mockReturnValue(true)
  await button('放弃草案').trigger('click')
  expect(signal?.aborted).toBe(true)
  pending.resolve(draft())
  await flushPromises()
  expect(wrapper.text()).toContain('还没有行程草案')
  expect(vi.mocked(requestJson).mock.calls.some(([path, init]) =>
    path === '/api/trips' && init?.method === 'POST',
  )).toBe(false)

  planning.vm.$emit('plan-generated', { ...draft(), budget_cny: 90 })
  await nextTick()
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  expect(wrapper.get('input[aria-label="草案门票预算"]').element).toHaveProperty('value', '90')
})

it('保存失败后须重新校验，保存期间只提交一次，成功后展示服务器快照', async () => {
  const plan = draft()
  const saved: SavedTrip = {
    ...plan, status: 'saved', trip_id: '67f49311-8552-4abc-8087-6f1158cb8efd',
    created_at: '2026-11-12T10:00:00+00:00', total_cny: 38,
    days: [{ ...plan.days[0], attractions: [attraction('a', 28), attraction('b')], subtotal_cny: 38 },
      ...plan.days.slice(1)],
  }
  const pending = deferred<SavedTrip>()
  let saveAttempts = 0
  vi.mocked(requestJson).mockImplementation(async (path, init) => {
    if (path === '/api/plans/validate') return plan
    if (path === '/api/trips' && init?.method === 'POST') {
      if (++saveAttempts === 1) throw new Error('行程文件暂时无法写入。')
      return pending.promise
    }
    return { items: [] }
  })
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  const wrapper = mount(TripWorkspace, { props: { draft: plan, attractions: [attraction('a', 5)] } })
  wrappers.push(wrapper)
  const button = (label: string) => wrapper.findAll('button').find(item => item.text() === label)!
  await button('确认保存行程').trigger('click')
  await flushPromises()
  expect(wrapper.get('.status').text()).toContain('保存失败')
  expect(wrapper.get('[role="alert"]').text()).toContain('行程文件暂时无法写入')
  expect(button('确认保存行程').attributes('disabled')).toBeDefined()
  expect(wrapper.find('.total').exists()).toBe(false)

  await button('重新校验行程').trigger('click')
  await flushPromises()
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  await button('确认保存行程').trigger('click')
  expect(wrapper.get('.status').text()).toBe('正在保存…')
  expect(button('放弃草案').attributes('disabled')).toBeDefined()
  await button('确认保存行程').trigger('click')
  expect(saveAttempts).toBe(2)

  pending.resolve(saved)
  await flushPromises()
  expect(wrapper.get('.status').text()).toBe('已保存')
  expect(wrapper.get('.place-info').text()).toContain('参考门票 ¥28')
  expect(wrapper.get('.total').text()).toContain('¥38')
  expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
})
