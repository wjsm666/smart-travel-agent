import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { requestJson } from '../../api/client'
import type { CandidateDay, PlanInput, PlanView } from '../../types/contracts'

export function toPlanInput(plan: PlanView): PlanInput {
  return {
    city: plan.city, day_count: plan.day_count, preferences: [...plan.preferences],
    budget_cny: plan.budget_cny, mode: plan.mode,
    days: plan.days.map(day => ({
      day: day.day, attraction_ids: day.attractions.map(item => item.id), note: day.note ?? null,
    })),
  }
}

/** Immutable local edits; a validation result belongs to exactly one revision. */
export function useDraftEditor() {
  const input = shallowRef<PlanInput | null>(null)
  const checked = shallowRef<PlanView | null>(null)
  const validating = ref(false)
  const error = ref('')
  let revision = 0
  let activeRequest = 0
  let controller: AbortController | undefined

  function invalidate() {
    revision++
    activeRequest++
    controller?.abort()
    validating.value = false
    checked.value = null
    error.value = ''
  }

  function load(plan: PlanView | null) {
    invalidate()
    input.value = plan ? toPlanInput(plan) : null
    // The parent supplies a server-validated draft. Editing immediately invalidates it.
    checked.value = plan
  }

  function editDays(days: CandidateDay[]) {
    if (!input.value) return
    invalidate()
    input.value = { ...input.value, days }
  }

  function add(dayNumber: number, id: string) {
    const plan = input.value
    const day = plan?.days.find(item => item.day === dayNumber)
    if (!plan || !day || !id || day.attraction_ids.length >= 2 ||
        plan.days.some(item => item.attraction_ids.includes(id))) return
    editDays(plan.days.map(item => item === day
      ? { ...item, attraction_ids: [...item.attraction_ids, id], note: null } : item))
  }

  function remove(dayNumber: number, id: string) {
    if (!input.value) return
    editDays(input.value.days.map(day => day.day === dayNumber
      ? { ...day, attraction_ids: day.attraction_ids.filter(value => value !== id), note: null } : day))
  }

  function move(from: number, to: number, id: string) {
    const plan = input.value
    const source = plan?.days.find(day => day.day === from)
    const target = plan?.days.find(day => day.day === to)
    if (!plan || !source?.attraction_ids.includes(id) || !target ||
        from === to || target.attraction_ids.length >= 2) return
    editDays(plan.days.map(day => day.day === from
      ? { ...day, attraction_ids: day.attraction_ids.filter(value => value !== id), note: null }
      : day.day === to ? { ...day, attraction_ids: [...day.attraction_ids, id], note: null } : day))
  }

  function reorder(dayNumber: number, index: number, offset: number) {
    const plan = input.value
    const target = plan?.days.find(day => day.day === dayNumber)
    const next = index + offset
    if (!plan || !target || index < 0 || index >= target.attraction_ids.length ||
        next < 0 || next >= target.attraction_ids.length) return
    const ids = [...target.attraction_ids]
    ;[ids[index], ids[next]] = [ids[next]!, ids[index]!]
    editDays(plan.days.map(day => day === target ? { ...day, attraction_ids: ids, note: null } : day))
  }

  function setNote(dayNumber: number, note: string) {
    if (!input.value) return
    editDays(input.value.days.map(day => day.day === dayNumber ? { ...day, note } : day))
  }

  function setBudget(budget: number) {
    if (!input.value) return
    invalidate()
    input.value = { ...input.value, budget_cny: budget }
  }

  async function validate() {
    if (!input.value || validating.value) return
    if (!Number.isInteger(input.value.budget_cny) || input.value.budget_cny < 0) {
      error.value = '门票预算需要填写非负整数。'
      return
    }
    const version = revision
    const requestId = ++activeRequest
    controller = new AbortController()
    validating.value = true
    error.value = ''
    try {
      const result = await requestJson<PlanView>('/api/plans/validate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input.value), signal: controller.signal,
      })
      if (version === revision && requestId === activeRequest) checked.value = result
    } catch (reason) {
      if (version === revision && requestId === activeRequest) {
        checked.value = null
        error.value = reason instanceof Error ? reason.message : '校验失败，请重试。'
      }
    } finally {
      if (requestId === activeRequest) validating.value = false
    }
  }

  onScopeDispose(invalidate)
  return {
    input, checked, validating, error, hasUnsavedChanges: computed(() => input.value !== null),
    load, add, remove, move, reorder, setNote, setBudget, validate,
  }
}
