import type { Attraction, PlanView } from '../src/types/contracts'

export function attraction(id: string, price: number | null = 10): Attraction {
  return {
    id, name: id, city: '汕头', category: '人文', description: '独立测试资料',
    area: '老城', duration_min: 120, ticket_cny: price, source_url: null,
    ticket_source_url: null, ticket_checked_at: null, ticket_note: null,
  }
}

export function draft(): PlanView {
  return {
    city: '汕头', day_count: 3, preferences: ['人文'], budget_cny: 50, mode: 'rules', status: 'draft',
    days: [
      { day: 1, attractions: [attraction('a'), attraction('b')], subtotal_cny: 20, note: '第一天旧建议' },
      { day: 2, attractions: [attraction('c', null)], subtotal_cny: 0, note: '第二天旧建议' },
      { day: 3, attractions: [], subtotal_cny: 0, note: '第三天保留建议' },
    ],
    total_cny: 20, has_unknown_prices: true, over_budget: null,
    warnings: ['费用仅包含已知参考门票，不含交通、餐饮和住宿。'],
  }
}

export function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}
