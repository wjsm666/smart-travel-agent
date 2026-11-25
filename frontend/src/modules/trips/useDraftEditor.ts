import { computed, onScopeDispose, shallowRef } from 'vue'
import { requestJson } from '../../api/client'
import type { CandidateDay, PlanInput, PlanView, SavedTrip } from '../../types/contracts'

export function toPlanInput(plan: PlanView | SavedTrip): PlanInput {
  return {
    city: plan.city, day_count: plan.day_count, preferences: [...plan.preferences],
    budget_cny: plan.budget_cny, mode: plan.mode,
    days: plan.days.map(day => ({
      day: day.day, attraction_ids: day.attractions.map(item => item.id), note: day.note ?? null,
    })),
  }
}

type DraftState =
  | { phase: 'empty' }
  | { phase: 'pending'; input: PlanInput }
  | { phase: 'validating'; input: PlanInput; request: AbortController }
  | { phase: 'validationFailed' | 'saveFailed'; input: PlanInput; message: string }
  | { phase: 'checked' | 'saving'; input: PlanInput; plan: PlanView }
  | { phase: 'saved'; input: PlanInput; trip: SavedTrip }

export function useDraftEditor() {
  const state = shallowRef<DraftState>({ phase: 'empty' })
  const phase = computed(() => state.value.phase)
  const input = computed(() => state.value.phase === 'empty' ? null : state.value.input)
  const checked = computed(() => 'plan' in state.value ? state.value.plan : null)
  const saved = computed(() => state.value.phase === 'saved' ? state.value.trip : null)
  const error = computed(() => 'message' in state.value ? state.value.message : '')
  const hasUnsavedChanges = computed(() => phase.value !== 'empty' && phase.value !== 'saved')
  const canSave = computed(() => state.value.phase === 'checked' &&
    state.value.plan.days.some(day => day.attractions.length > 0))

  function replaceState(next: DraftState) {
    const previous = state.value
    state.value = next
    if (previous.phase === 'validating') previous.request.abort()
  }

  function load(plan: PlanView | null) {
    replaceState(plan
      ? { phase: 'checked', input: toPlanInput(plan), plan }
      : { phase: 'empty' })
  }

  function editableInput() {
    return phase.value === 'saving' || phase.value === 'saved' ? null : input.value
  }

  function editDays(plan: PlanInput, days: CandidateDay[]) {
    replaceState({ phase: 'pending', input: { ...plan, days } })
  }

  function add(dayNumber: number, id: string) {
    const plan = editableInput()
    const day = plan?.days.find(item => item.day === dayNumber)
    if (!plan || !day || !id || day.attraction_ids.length >= 2 ||
        plan.days.some(item => item.attraction_ids.includes(id))) return
    editDays(plan, plan.days.map(item => item === day
      ? { ...item, attraction_ids: [...item.attraction_ids, id], note: null } : item))
  }

  function remove(dayNumber: number, id: string) {
    const plan = editableInput()
    if (!plan?.days.some(day => day.day === dayNumber && day.attraction_ids.includes(id))) return
    editDays(plan, plan.days.map(day => day.day === dayNumber
      ? { ...day, attraction_ids: day.attraction_ids.filter(value => value !== id), note: null } : day))
  }

  function move(from: number, to: number, id: string) {
    const plan = editableInput()
    const source = plan?.days.find(day => day.day === from)
    const target = plan?.days.find(day => day.day === to)
    if (!plan || !source?.attraction_ids.includes(id) || !target ||
        from === to || target.attraction_ids.length >= 2) return
    editDays(plan, plan.days.map(day => day.day === from
      ? { ...day, attraction_ids: day.attraction_ids.filter(value => value !== id), note: null }
      : day.day === to ? { ...day, attraction_ids: [...day.attraction_ids, id], note: null } : day))
  }

  function reorder(dayNumber: number, index: number, offset: number) {
    const plan = editableInput()
    const target = plan?.days.find(day => day.day === dayNumber)
    const next = index + offset
    if (!plan || !target || index < 0 || index >= target.attraction_ids.length ||
        next < 0 || next >= target.attraction_ids.length) return
    const ids = [...target.attraction_ids]
    ;[ids[index], ids[next]] = [ids[next]!, ids[index]!]
    editDays(plan, plan.days.map(day => day === target
      ? { ...day, attraction_ids: ids, note: null } : day))
  }

  function setNote(dayNumber: number, note: string) {
    const plan = editableInput()
    if (!plan?.days.some(day => day.day === dayNumber && day.note !== note)) return
    editDays(plan, plan.days.map(day => day.day === dayNumber ? { ...day, note } : day))
  }

  function setBudget(budget: number) {
    const plan = editableInput()
    if (!plan || Object.is(plan.budget_cny, budget)) return
    replaceState({ phase: 'pending', input: { ...plan, budget_cny: budget } })
  }

  async function validate() {
    const plan = editableInput()
    if (!plan || phase.value === 'validating') return
    if (!Number.isInteger(plan.budget_cny) || plan.budget_cny < 0) {
      state.value = {
        phase: 'validationFailed', input: plan, message: '门票预算需要填写非负整数。',
      }
      return
    }
    const request = new AbortController()
    // A replaced or edited draft no longer owns this request, even if it still resolves.
    const attempt = { phase: 'validating' as const, input: plan, request }
    state.value = attempt
    try {
      const result = await requestJson<PlanView>('/api/plans/validate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(plan), signal: request.signal,
      })
      if (state.value === attempt) state.value = { phase: 'checked', input: plan, plan: result }
    } catch (reason) {
      if (state.value === attempt) {
        state.value = {
          phase: 'validationFailed', input: plan,
          message: reason instanceof Error ? reason.message : '校验失败，请重试。',
        }
      }
    }
  }

  async function save() {
    const current = state.value
    if (current.phase !== 'checked' || !canSave.value) return
    const attempt = { ...current, phase: 'saving' as const }
    state.value = attempt
    try {
      const trip = await requestJson<SavedTrip>('/api/trips', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(current.input),
      })
      if (state.value === attempt) state.value = { phase: 'saved', input: toPlanInput(trip), trip }
      return trip
    } catch (reason) {
      if (state.value === attempt) {
        state.value = {
          phase: 'saveFailed', input: current.input,
          message: reason instanceof Error ? reason.message : '保存失败，请重试。',
        }
      }
    }
  }

  onScopeDispose(() => load(null))
  return {
    phase, input, checked, error, saved, canSave, hasUnsavedChanges,
    load, add, remove, move, reorder, setNote, setBudget, validate, save,
  }
}
