<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'
import { requestJson } from '../../api/client'
import type { SavedTrip } from '../../types/contracts'

const emit = defineEmits<{ deleted: [tripId: string] }>()
const trips = shallowRef<SavedTrip[]>([])
const detail = shallowRef<SavedTrip | null>(null)
const busy = ref(false)
const error = ref('')
const notice = ref('')
let listRequest = 0

function message(reason: unknown) {
  return reason instanceof Error ? reason.message : '无法读取或更新行程记录，请重试。'
}

async function refresh() {
  const request = ++listRequest
  busy.value = true
  error.value = ''
  try {
    const { items } = await requestJson<{ items: SavedTrip[] }>('/api/trips')
    if (request !== listRequest) return
    trips.value = items
    if (detail.value && !items.some(trip => trip.trip_id === detail.value?.trip_id)) detail.value = null
  } catch (reason) {
    if (request === listRequest) error.value = message(reason)
  } finally {
    if (request === listRequest) busy.value = false
  }
}

const acting = ref(false)
async function open(trip: SavedTrip) {
  if (acting.value) return
  acting.value = true
  detail.value = null
  error.value = ''
  notice.value = ''
  try {
    detail.value = await requestJson<SavedTrip>(`/api/trips/${encodeURIComponent(trip.trip_id)}`)
  } catch (reason) {
    error.value = message(reason)
  } finally {
    acting.value = false
  }
}

async function remove(trip: SavedTrip) {
  if (acting.value || !window.confirm('确定删除这条已保存的行程？')) return
  acting.value = true
  error.value = ''
  notice.value = ''
  try {
    await requestJson<void>(`/api/trips/${encodeURIComponent(trip.trip_id)}`, { method: 'DELETE' })
    trips.value = trips.value.filter(item => item.trip_id !== trip.trip_id)
    if (detail.value?.trip_id === trip.trip_id) detail.value = null
    emit('deleted', trip.trip_id)
    notice.value = '已删除行程。'
    await refresh()
  } catch (reason) {
    error.value = message(reason)
  } finally {
    acting.value = false
  }
}

const localTime = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
onMounted(refresh)
defineExpose({ refresh })
</script>

<template>
  <section class="history" aria-labelledby="history-heading">
    <header>
      <h3 id="history-heading">历史行程</h3>
      <button type="button" :disabled="busy || acting" @click="refresh">刷新历史</button>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="busy || acting" role="status">正在处理历史行程…</p>
    <p v-else-if="!trips.length && !error" role="status">还没有已保存的行程。</p>
    <ul v-if="trips.length" class="records">
      <li v-for="trip in trips" :key="trip.trip_id">
        <div><strong>{{ trip.city }} · {{ trip.day_count }} 天</strong>
          <span>{{ localTime.format(new Date(trip.created_at)) }} · 已知参考门票 ¥{{ trip.total_cny }}</span></div>
        <div class="actions">
          <button type="button" :disabled="busy || acting" @click="open(trip)">查看详情</button>
          <button type="button" class="delete" :disabled="busy || acting" @click="remove(trip)">删除行程</button>
        </div>
      </li>
    </ul>
    <article v-if="detail" class="snapshot" aria-label="历史行程详情">
      <header><h4>{{ detail.city }} · {{ detail.day_count }} 天行程快照</h4>
        <button type="button" @click="detail = null">关闭详情</button></header>
      <p>{{ detail.mode === 'agent' ? 'AI 推荐' : '规则推荐' }} · 门票预算 ¥{{ detail.budget_cny }}
        · 已知参考门票 ¥{{ detail.total_cny }} ·
        {{ detail.over_budget === true ? '已知门票超出预算' : detail.over_budget === null ? '预算待确认' : '已知门票在预算内' }}</p>
      <section v-for="day in detail.days" :key="day.day">
        <h5>第 {{ day.day }} 天 · 已知参考门票 ¥{{ day.subtotal_cny }}</h5>
        <ol v-if="day.attractions.length">
          <li v-for="item in day.attractions" :key="item.id">{{ item.name }} · {{ item.area }} ·
            {{ item.ticket_cny === null ? '门票待确认' : `参考门票 ¥${item.ticket_cny}` }}</li>
        </ol>
        <p v-else>这一天暂未安排景点。</p>
        <p v-if="day.note">{{ day.note }}</p>
      </section>
      <ul><li v-for="warning in detail.warnings" :key="warning">{{ warning }}</li></ul>
    </article>
  </section>
</template>

<style scoped>
.history{margin-top:28px;border-top:1px solid #e5edf5;padding-top:18px;color:#172e4b}
header,.records>li{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
h3,h4{margin:4px 0}h5{margin:16px 0 6px;font-size:14px}
p,li{font-size:14px;line-height:1.6}p{overflow-wrap:anywhere}
.records{list-style:none;padding:0}.records>li{padding:12px 0;border-bottom:1px solid #e5edf5}
.records span{display:block;color:#5c7189}.actions{display:flex;gap:8px}
button{border:1px solid #cbd9e9;background:#fff;color:#365e8a;border-radius:6px;padding:6px 10px}
button:disabled{opacity:.55}.delete,.error{color:#a33d39}
.snapshot{margin-top:16px;padding:16px;background:#f3f7fc;border-radius:8px}
</style>
