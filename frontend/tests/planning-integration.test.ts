import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from '../src/App.vue'
import PlanningPanel from '../src/modules/planning/PlanningPanel.vue'
import { requestJson } from '../src/api/client'
import { attraction, deferred, draft } from './fixtures'
import type { PlanView } from '../src/types/contracts'

vi.mock('../src/api/client', () => ({ requestJson: vi.fn() }))
const wrappers: ReturnType<typeof mount>[] = []

afterEach(() => {
  wrappers.splice(0).forEach(wrapper => wrapper.unmount())
  vi.mocked(requestJson).mockReset()
})

it('规划页查询和筛选保留完整景点交接，未知票价与来源链接正确展示', async () => {
  const first = { ...attraction('小公园', 0), source_url: 'https://example.com/place',
    ticket_source_url: 'https://example.com/ticket' }
  const second = { ...attraction('未知票价', null), source_url: 'javascript:alert(1)',
    ticket_source_url: 'data:text/html,unsafe' }
  vi.mocked(requestJson).mockResolvedValue({ items: [first, second] })
  const wrapper = mount(PlanningPanel)
  wrappers.push(wrapper)
  await flushPromises()

  expect(wrapper.emitted('catalog-loaded')).toEqual([[[first, second]]])
  expect(wrapper.text()).toContain('参考免费')
  expect(wrapper.text()).toContain('门票待确认')
  const links = wrapper.findAll('.reference-links a')
  expect(links.map(link => link.attributes('href'))).toEqual([
    'https://example.com/place', 'https://example.com/ticket',
  ])
  expect(links.every(link => link.attributes('rel') === 'noopener noreferrer')).toBe(true)
  await wrapper.get('input[aria-label="搜索景点"]').setValue('小公园')
  expect(wrapper.findAll('.place')).toHaveLength(1)
  await wrapper.get('input[aria-label="搜索景点"]').setValue('不存在')
  expect(wrapper.text()).toContain('没有找到符合条件的景点')
  expect(wrapper.emitted('catalog-loaded')).toHaveLength(1)
})

it('实际规划组件生成规则草案并交给 A 工作区，替换取消保留当前修改', async () => {
  const plan = draft()
  const replacement = { ...draft(), budget_cny: 300 }
  let generationCount = 0
  vi.mocked(requestJson).mockImplementation(async (path, init) => {
    if (path.startsWith('/api/attractions')) return { items: [attraction('备用景点')] }
    if (path === '/api/trips') return { items: [] }
    expect(path).toBe('/api/plans/generate')
    expect(JSON.parse(String(init?.body))).toEqual({
      city: '汕头', day_count: 3, preferences: ['人文'], budget_cny: 200, mode: 'rules',
    })
    return generationCount++ ? replacement : plan
  })
  const wrapper = mount(App, { global: { stubs: {
    ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue" role="dialog"><slot /><slot name="footer" /></div>' },
  } } })
  wrappers.push(wrapper)
  await flushPromises()
  await wrapper.get('.day-options button:nth-child(3)').trigger('click')
  await wrapper.get('.interest-options button:nth-child(2)').trigger('click')
  await wrapper.get('.secondary-button').trigger('click')
  await flushPromises()
  expect(wrapper.get('#trip-workspace').text()).toContain('规则推荐')
  expect(wrapper.get('.plan-link a').attributes('href')).toBe('#trip-workspace')
  expect(wrapper.get('select[aria-label="第3天添加景点"]').text()).toContain('备用景点')
  await wrapper.get('textarea[aria-label="第1天说明"]').setValue('保留我的修改')
  await wrapper.get('.secondary-button').trigger('click')
  await flushPromises()
  expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  await wrapper.get('[role="dialog"] button').trigger('click')
  expect(wrapper.get('textarea[aria-label="第1天说明"]').element).toHaveProperty('value', '保留我的修改')
  expect(wrapper.get('input[aria-label="草案门票预算"]').element).toHaveProperty('value', '50')
})

it('AI 请求期间禁止重复生成，失败如实提示，规则推荐需用户主动选择', async () => {
  const pending = deferred<PlanView>()
  vi.mocked(requestJson).mockImplementation(async (path, init) => {
    if (path.startsWith('/api/attractions')) return { items: [attraction('a')] }
    const mode = JSON.parse(String(init?.body)).mode
    return mode === 'agent' ? pending.promise : draft()
  })
  const wrapper = mount(PlanningPanel)
  wrappers.push(wrapper)
  await flushPromises()
  await wrapper.get('#planning-form').trigger('submit')
  expect(wrapper.get('.primary-button').text()).toContain('AI 正在生成')
  expect(wrapper.get('.secondary-button').attributes('disabled')).toBeDefined()
  await wrapper.get('#planning-form').trigger('submit')
  expect(vi.mocked(requestJson).mock.calls.filter(([path]) => path === '/api/plans/generate')).toHaveLength(1)
  pending.reject(new Error('未配置模型名称或密钥，请先配置模型服务。'))
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('未配置模型名称或密钥')
  expect(wrapper.emitted('plan-generated')).toBeUndefined()
  expect(vi.mocked(requestJson).mock.calls.filter(([path]) => path === '/api/plans/generate')).toHaveLength(1)
  await wrapper.get('.secondary-button').trigger('click')
  await flushPromises()
  expect(wrapper.emitted('plan-generated')).toEqual([[draft()]])
})

it('景点资料未就绪时，表单提交不能绕过生成按钮的限制', async () => {
  const catalog = deferred<{ items: ReturnType<typeof attraction>[] }>()
  vi.mocked(requestJson).mockReturnValueOnce(catalog.promise)
  const wrapper = mount(PlanningPanel)
  wrappers.push(wrapper)
  await wrapper.get('#planning-form').trigger('submit')
  expect(vi.mocked(requestJson).mock.calls.map(([path]) => path)).toEqual(['/api/attractions?city=汕头'])
  catalog.resolve({ items: [] })
  await flushPromises()
  await wrapper.get('#planning-form').trigger('submit')
  expect(requestJson).toHaveBeenCalledTimes(1)
  expect(wrapper.emitted('plan-generated')).toBeUndefined()
})
