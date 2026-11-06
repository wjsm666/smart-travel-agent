<script setup lang="ts">
import { computed, watch } from 'vue'
import { ElButton } from 'element-plus'
import 'element-plus/es/components/button/style/css'
import type { Attraction, PlanView } from '../../types/contracts'
import { useDraftEditor } from './useDraftEditor'

const props = defineProps<{ draft: PlanView | null; attractions: Attraction[] }>()
const {
  input, checked, validating, error, hasUnsavedChanges,
  load, add, remove, move, reorder, setNote, setBudget, validate,
} = useDraftEditor()
watch(() => props.draft, load, { immediate: true })
defineExpose({ hasUnsavedChanges })

// Fall back to the generated snapshots if the catalog is temporarily unavailable.
const catalog = computed(() => new Map([
  ...(props.draft?.days.flatMap(day => day.attractions) ?? []), ...props.attractions,
].map(item => [item.id, item])))
const usedIds = computed(() => new Set(input.value?.days.flatMap(day => day.attraction_ids) ?? []))
const available = computed(() => [...catalog.value.values()]
  .filter(item => item.city === input.value?.city && !usedIds.value.has(item.id)))
const budgetLabel = computed(() => checked.value?.over_budget === true ? '已知门票超出预算'
  : checked.value?.over_budget === null ? '预算待确认' : '已知门票在预算内')

function textValue(event: Event): string {
  return (event.target as HTMLInputElement).value
}
function addSelected(day: number, event: Event) {
  add(day, textValue(event))
  ;(event.target as HTMLSelectElement).value = ''
}
function moveSelected(day: number, id: string, event: Event) {
  move(day, Number(textValue(event)), id)
  ;(event.target as HTMLSelectElement).value = ''
}
function ticketLabel(item: Attraction | undefined): string {
  if (!item || item.ticket_cny === null) return '门票待确认'
  return item.ticket_cny === 0 ? '参考免费' : `参考门票 ¥${item.ticket_cny}`
}
</script>

<template>
  <section id="trip-workspace" class="workspace" aria-labelledby="workspace-title">
    <header class="workspace-head">
      <div><span class="eyebrow">我的行程</span><h2 id="workspace-title">把草案调整成你的安排</h2>
        <p>每一天最多两处景点，安排有变动后请重新校验门票与游览限制。</p></div>
      <span v-if="input" class="source">{{ input.mode === 'agent' ? 'AI 推荐' : '规则推荐' }} · 可手动调整</span>
    </header>

    <div v-if="!input" class="empty" role="status">还没有行程草案。请在上方填写需求，选择一种方式生成。</div>
    <template v-else>
      <div class="toolbar">
        <span>{{ input.city }} · {{ input.day_count }} 天</span>
        <label>门票预算 <input aria-label="草案门票预算" type="number" min="0" step="1"
          :value="input.budget_cny" @input="setBudget(textValue($event).trim() ? Number(textValue($event)) : NaN)"> 元 / 人</label>
        <span class="status" :class="{ pending: !checked }" role="status">
          {{ validating ? '正在校验…' : checked ? '已校验 · 尚未保存' : '待校验 · 尚未保存' }}
        </span>
      </div>

      <div class="days">
        <article v-for="day in input.days" :key="day.day" class="day">
          <header><h3>第 {{ day.day }} 天</h3><span>{{ day.attraction_ids.length }} / 2 处</span></header>
          <p v-if="!day.attraction_ids.length" class="day-empty">这一天暂未安排景点。</p>
          <ol>
            <li v-for="(id, index) in day.attraction_ids" :key="id">
              <div class="place-info"><strong>{{ catalog.get(id)?.name ?? id }}</strong>
                <span>{{ catalog.get(id)?.area }} · {{ ticketLabel(catalog.get(id)) }}</span>
                <small v-if="catalog.get(id)?.duration_min">参考游览 {{ catalog.get(id)?.duration_min }} 分钟</small>
              </div>
              <div class="edit-actions">
                <button type="button" :disabled="index === 0" :aria-label="`上移${catalog.get(id)?.name ?? id}`"
                  @click="reorder(day.day, index, -1)">上移</button>
                <button type="button" :disabled="index === day.attraction_ids.length - 1"
                  :aria-label="`下移${catalog.get(id)?.name ?? id}`" @click="reorder(day.day, index, 1)">下移</button>
                <select v-if="input.day_count > 1" value="" :aria-label="`移动${catalog.get(id)?.name ?? id}到其他日期`"
                  @change="moveSelected(day.day, id, $event)">
                  <option value="" disabled>移到…</option>
                  <option v-for="target in input.days.filter(item => item.day !== day.day)" :key="target.day"
                    :value="target.day" :disabled="target.attraction_ids.length >= 2">第 {{ target.day }} 天</option>
                </select>
                <button type="button" class="remove" :aria-label="`移除${catalog.get(id)?.name ?? id}`" @click="remove(day.day, id)">移除</button>
              </div>
            </li>
          </ol>
          <label class="add-label">添加景点
            <select value="" :aria-label="`第${day.day}天添加景点`"
              :disabled="day.attraction_ids.length >= 2 || !available.length" @change="addSelected(day.day, $event)">
              <option value="" disabled>{{ day.attraction_ids.length >= 2 ? '当日已满两处景点' : available.length ? '选择未安排的汕头景点' : '暂无未安排的景点' }}</option>
              <option v-for="item in available" :key="item.id" :value="item.id">{{ item.name }} · {{ item.area }}</option>
            </select>
          </label>
          <label class="note-label">当天说明
            <textarea :aria-label="`第${day.day}天说明`" :value="day.note ?? ''" maxlength="240" rows="2"
              placeholder="填写当天安排，最多 240 字" @input="setNote(day.day, textValue($event))"></textarea>
          </label>
          <p v-if="checked" class="subtotal">已知参考门票 ¥{{ checked.days.find(item => item.day === day.day)?.subtotal_cny }}
            <span v-if="checked.days.find(item => item.day === day.day)?.attractions.some(item => item.ticket_cny === null)"> · 另有门票待确认</span></p>
        </article>
      </div>

      <div class="summary" aria-live="polite">
        <template v-if="checked">
          <div class="total"><span>{{ checked.has_unknown_prices ? '已知参考门票合计' : '参考门票合计' }}</span>
            <strong>¥{{ checked.total_cny }}</strong><span :class="{ warning: checked.over_budget !== false }">{{ budgetLabel }}</span></div>
          <ul class="warnings"><li v-for="message in checked.warnings" :key="message">{{ message }}</li></ul>
        </template>
        <p v-else>当前安排尚未通过校验，门票合计和预算状态将在校验成功后更新。</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <ElButton type="primary" :loading="validating" :disabled="validating" @click="validate">重新校验行程</ElButton>
      </div>
      <p class="boundary">草案暂不支持保存，刷新页面会丢失当前安排。景点资料和门票并非实时信息，费用不包含交通、餐饮和住宿。</p>
    </template>
  </section>
</template>

<style scoped>
.workspace{max-width:1344px;margin:0 auto 48px;padding:30px;box-sizing:border-box;border:1px solid #dbe5f0;border-radius:16px;background:#fff;color:#172e4b}
.workspace *{box-sizing:border-box}.workspace-head{display:flex;justify-content:space-between;gap:20px;align-items:start}.eyebrow{font-size:12px;font-weight:700;color:#1769dc}h2{margin:8px 0;font-size:24px}.workspace-head p,.boundary{color:#5c7189;font-size:13px;line-height:1.8}.source{border-radius:20px;padding:9px 13px;background:#eaf3ff;color:#2468c3;font-size:12px;white-space:nowrap}.empty{padding:48px 0;text-align:center;color:#5c7189}.toolbar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;border-block:1px solid #e5edf5;padding:18px 0;margin:20px 0}.toolbar label{font-size:13px}.toolbar input{width:110px;margin:0 6px;padding:8px;border:1px solid #cbd9e9;border-radius:6px}.status{margin-left:auto;color:#226d60;font-size:13px}.status.pending{color:#98631b}.days{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.day{border:1px solid #dbe5f0;border-radius:12px;padding:20px;min-width:0}.day>header{display:flex;justify-content:space-between;align-items:center}.day h3{margin:0;font-size:19px}.day>header>span,.day-empty{color:#6c8198;font-size:13px}.day ol{list-style:none;margin:16px 0;padding:0}.day li{padding:14px 0;border-bottom:1px solid #edf2f7}.place-info{display:flex;flex-direction:column;gap:7px}.place-info span,.place-info small{color:#5c7189;font-size:12px}.edit-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}.edit-actions button,.edit-actions select{padding:6px 8px;border:1px solid #d5e1ef;background:white;color:#365e8a;border-radius:6px;font-size:12px}.edit-actions .remove{color:#a33d39}.add-label,.note-label{display:flex;flex-direction:column;gap:8px;font-size:13px;margin-top:16px}.add-label select,.note-label textarea{width:100%;padding:10px;border:1px solid #cbd9e9;border-radius:7px;color:#365e8a;background:white}.note-label textarea{resize:vertical;line-height:1.6}.subtotal{margin-bottom:0;font-size:13px;color:#365e8a}.subtotal span{color:#98631b}.summary{padding:22px;margin-top:22px;border-radius:12px;background:#f3f7fc;line-height:1.7;font-size:14px}.total{display:flex;align-items:center;gap:15px;flex-wrap:wrap}.total strong{font-size:28px;color:#1769dc}.total>span:last-child{color:#226d60}.total>span.warning{color:#98631b}.warnings{padding-left:20px;color:#5c7189;font-size:13px}.error{background:#fff1ee;color:#a33d39;padding:12px;border-radius:8px}.boundary{margin:18px 0 0}
@media(min-width:1440px){.workspace{max-width:1344px}}
@media(max-width:1439px){.workspace{margin-inline:48px}}
@media(max-width:900px){.workspace{margin-inline:24px}.days{grid-template-columns:1fr}.workspace-head{flex-wrap:wrap}}
@media(max-width:620px){.workspace{margin-inline:16px;padding:20px}.toolbar{gap:12px}.status{margin-left:0}.day{padding:16px}h2{font-size:21px}}
</style>
