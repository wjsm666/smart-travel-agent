import { afterEach, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../src/App.vue'
import TripWorkspace from '../src/modules/trips/TripWorkspace.vue'
import PlanningPanel from '../src/modules/planning/PlanningPanel.vue'
import { draft } from './fixtures'

vi.mock('../src/api/client', () => ({ requestJson: vi.fn() }))
const wrappers: ReturnType<typeof mount>[] = []
afterEach(() => wrappers.splice(0).forEach(wrapper => wrapper.unmount()))

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
