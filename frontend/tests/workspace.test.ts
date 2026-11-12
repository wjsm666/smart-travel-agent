import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../src/App.vue'
import TripWorkspace from '../src/modules/trips/TripWorkspace.vue'
import PlanningPanel from '../src/modules/planning/PlanningPanel.vue'
import { requestJson } from '../src/api/client'
import type { SavedTrip } from '../src/types/contracts'
import { draft } from './fixtures'

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
})
