<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { requestJson } from '../../api/client'
import type { Attraction, GenerationRequest, PlanView } from '../../types/contracts'

type Category = Attraction['category']
const emit = defineEmits<{
  (event: 'catalog-loaded', attractions: Attraction[]): void
  (event: 'plan-generated', plan: PlanView): void
}>()

const categories: Category[] = ['自然', '人文', '休闲']
const attractions = ref<Attraction[]>([])
const catalogLoading = ref(false)
const generatingMode = ref<GenerationRequest['mode'] | null>(null)
const generating = computed(() => generatingMode.value !== null)
const catalogError = ref('')
const generationError = ref('')
const hasGeneratedPlan = ref(false)
const keyword = ref('')
const categoryFilter = ref<Category | ''>('')
const showAll = ref(false)
const form = reactive({ city: '汕头', day_count: 2, preferences: [] as Category[], budget_cny: 200 })

const filteredAttractions = computed(() => {
  const search = keyword.value.trim()
  return attractions.value.filter(item =>
    item.city === '汕头' &&
    (!categoryFilter.value || item.category === categoryFilter.value) &&
    (!search || item.name.includes(search) || item.description.includes(search)),
  )
})
const visibleAttractions = computed(() => showAll.value ? filteredAttractions.value : filteredAttractions.value.slice(0, 6))
const attractionCards = computed(() => visibleAttractions.value.map(item => ({
  item,
  source: referenceLink(item.source_url),
  ticketSource: referenceLink(item.ticket_source_url),
})))

function referenceLink(value: string | null): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  } catch {
    return null
  }
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}
function togglePreference(category: Category) {
  if (generating.value) return
  form.preferences = form.preferences.includes(category)
    ? form.preferences.filter(value => value !== category)
    : [...form.preferences, category]
}
function chooseFilter(category: Category | '') {
  categoryFilter.value = category
  showAll.value = false
}
function ticketLabel(item: Attraction): string {
  if (item.ticket_cny == null) return '门票待确认'
  return item.ticket_cny === 0 ? '参考免费' : `参考门票 ¥${item.ticket_cny}`
}
async function loadCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const result = await requestJson<{ items: Attraction[] }>('/api/attractions?city=汕头')
    attractions.value = result.items
    emit('catalog-loaded', result.items)
  } catch (error) {
    catalogError.value = errorMessage(error, '景点资料暂时无法加载，请重试。')
  } finally {
    catalogLoading.value = false
  }
}
async function generate(mode: GenerationRequest['mode']) {
  if (generating.value) return
  generationError.value = ''
  if (!Number.isInteger(form.day_count) || form.day_count < 1 || form.day_count > 5) {
    generationError.value = '请选择 1 至 5 天的行程。'
    return
  }
  if (!Number.isInteger(form.budget_cny) || form.budget_cny < 0) {
    generationError.value = '门票预算需要填写非负整数。'
    return
  }
  generatingMode.value = mode
  try {
    const payload: GenerationRequest = { ...form, preferences: [...form.preferences], mode }
    const plan = await requestJson<PlanView>('/api/plans/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    })
    emit('plan-generated', plan)
    hasGeneratedPlan.value = true
  } catch (error) {
    generationError.value = errorMessage(error, '行程暂时无法生成，请稍后重试。')
  } finally {
    generatingMode.value = null
  }
}
onMounted(loadCatalog)
</script>

<template>
  <section class="travel" aria-labelledby="planning-title">
    <header class="topbar">
      <div class="wordmark"><strong>汕头行程</strong><span>城市旅行计划</span></div>
      <div class="destination"><span class="location-dot"></span>汕头，广东</div>
    </header>

    <div class="workspace">
      <div class="page-intro"><div><p class="eyebrow">汕头旅行 / 行程规划</p><h1 id="planning-title">规划一段汕头之行</h1><p>告诉我们你的时间和喜好，生成后还可以按自己的想法调整。</p></div><div class="intro-note"><span>目的地</span><strong>汕头</strong></div></div>

      <div class="workspace-grid">
        <section class="planner" aria-labelledby="form-title">
          <div class="panel-heading"><div><h2 id="form-title">先定下旅行偏好</h2><p>这些信息会帮助我们安排更适合你的行程。</p></div><span class="step-label">行程设置</span></div>
          <form id="planning-form" @submit.prevent="generate('agent')">
            <fieldset class="field-block"><legend>准备玩几天？</legend><p class="field-description">可选择 1 至 5 天</p><div class="day-options"><button v-for="day in 5" :key="day" type="button" class="day-option" :class="{ selected: form.day_count === day }" :aria-pressed="form.day_count === day" :disabled="generating" @click="form.day_count = day"><strong>{{ day }}</strong><span>天</span></button></div></fieldset>
            <fieldset class="field-block preferences"><legend>旅行中更喜欢什么？<span>可多选</span></legend><p class="field-description">没有特别偏好也可以跳过。</p><div class="interest-options"><button v-for="category in categories" :key="category" type="button" class="interest" :class="{ selected: form.preferences.includes(category) }" :aria-pressed="form.preferences.includes(category)" :disabled="generating" @click="togglePreference(category)"><span class="interest-indicator" aria-hidden="true">{{ form.preferences.includes(category) ? '✓' : '+' }}</span><span class="interest-copy"><strong>{{ category }}</strong><small>{{ category === '自然' ? '山海、岛屿与风景' : category === '人文' ? '老城、建筑与故事' : '公园与轻松漫游' }}</small></span></button></div></fieldset>
            <div class="field-block budget"><label for="trip-budget">门票预算</label><p class="field-description">每人预计的景点门票费用，不含交通、餐饮与住宿。</p><div class="budget-row"><div class="budget-input"><span>¥</span><input id="trip-budget" v-model.number="form.budget_cny" type="number" min="0" step="1" :disabled="generating" aria-describedby="budget-help"><span>元 / 人</span></div><div class="budget-suggestions" aria-label="常用预算"><button v-for="amount in [100, 200, 300]" :key="amount" type="button" :disabled="generating" :class="{ active: form.budget_cny === amount }" @click="form.budget_cny = amount">¥{{ amount }}</button></div></div><small id="budget-help">未确认票价的景点会单独提示。</small></div>
          </form>
        </section>

        <aside class="summary" aria-label="旅行设置摘要">
          <div><div class="summary-top"><span>你的旅行</span><span class="summary-location"><span class="location-dot"></span>广东 · 汕头</span></div><h2>汕头</h2><p class="summary-caption">山海、老城，还有街巷里的烟火气。</p><div class="summary-divider"></div><dl class="summary-list"><div><dt>游玩天数</dt><dd>{{ form.day_count }} 天</dd></div><div><dt>门票预算</dt><dd>{{ Number.isInteger(form.budget_cny) && form.budget_cny >= 0 ? `¥${form.budget_cny} / 人` : '待填写' }}</dd></div><div><dt>旅行偏好</dt><dd>{{ form.preferences.length ? form.preferences.join('、') : '不限' }}</dd></div></dl><p class="summary-note">景点资料为人工整理，票价、开放时间和交通请在出发前核实。</p></div>
          <div class="summary-actions">
            <div v-if="generationError" class="error" role="alert">{{ generationError }}</div>
            <button class="primary-button" type="submit" form="planning-form" :disabled="generating || catalogLoading || !attractions.length">
              {{ generatingMode === 'agent' ? 'AI 正在生成…' : 'AI 生成行程' }}
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h11M11 5l5 5-5 5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <button class="secondary-button" type="button" :disabled="generating || catalogLoading || !attractions.length" @click="generate('rules')">
              {{ generatingMode === 'rules' ? '正在按规则生成…' : '使用规则推荐' }}
            </button>
            <p v-if="hasGeneratedPlan" class="plan-link">
              <a href="#trip-workspace">前往行程工作区 <span aria-hidden="true">↓</span></a>
            </p>
            <p>生成后可继续调整，确认后才会保存。</p>
          </div>
        </aside>
      </div>

      <section class="discover" aria-labelledby="discover-title">
        <div class="discover-head"><div><p class="eyebrow">发现汕头</p><h2 id="discover-title">看看有哪些地方</h2><p>从老城街巷到海边山色，先了解你可能感兴趣的景点。</p></div><label class="search"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.3" stroke="currentColor" stroke-width="1.6"/><path d="m16 16 4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg><input v-model="keyword" type="search" placeholder="搜索景点" aria-label="搜索景点"></label></div>
        <div class="filters" role="group" aria-label="筛选景点类别"><button type="button" :class="{ active: !categoryFilter }" :aria-pressed="!categoryFilter" @click="chooseFilter('')">全部景点</button><button v-for="category in categories" :key="category" type="button" :class="{ active: categoryFilter === category }" :aria-pressed="categoryFilter === category" @click="chooseFilter(category)">{{ category }}</button><span class="filter-count">{{ filteredAttractions.length }} 处景点</span></div>
        <p v-if="catalogError" class="error" role="alert">{{ catalogError }} <button type="button" class="retry" @click="loadCatalog">重新加载</button></p><p v-else-if="catalogLoading" class="empty" role="status">正在加载景点资料…</p><p v-else-if="!filteredAttractions.length" class="empty">没有找到符合条件的景点，换个关键词试试。</p>
        <div v-else class="places">
          <article v-for="{ item, source, ticketSource } in attractionCards" :key="item.id" class="place">
            <div class="place-main">
              <div class="place-meta">
                <span class="place-category">{{ item.category }}</span>
                <span>{{ item.area || '汕头' }}</span>
              </div>
              <h3>{{ item.name }}</h3>
              <p>{{ item.description }}</p>
              <p v-if="item.ticket_note" class="price-note">{{ item.ticket_note }}</p>
              <div v-if="source || ticketSource" class="reference-links">
                <a v-if="source" :href="source" target="_blank" rel="noopener noreferrer"
                  :aria-label="`${item.name}景点来源（新窗口）`">景点来源</a>
                <a v-if="ticketSource" :href="ticketSource" target="_blank" rel="noopener noreferrer"
                  :aria-label="`${item.name}票价来源（新窗口）`">票价来源</a>
              </div>
            </div>
            <div class="place-details">
              <span>{{ item.duration_min ? `建议 ${Math.round(item.duration_min / 6) / 10} 小时` : '时长待确认' }}</span>
              <strong>{{ ticketLabel(item) }}</strong>
              <small v-if="item.ticket_checked_at">核对于 {{ item.ticket_checked_at }}</small>
            </div>
          </article>
        </div>
        <button v-if="filteredAttractions.length > 6" class="more-button" type="button" @click="showAll = !showAll">{{ showAll ? '收起景点' : `查看更多景点（${filteredAttractions.length - 6}）` }}</button><div class="data-note">景点资料为人工整理，仅供行程规划参考。票价、开放状态和交通请在出发前核实。</div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.travel { --ink:#1e302b; --muted:#71817a; --accent:#2b5e50; --line:#e5ebe4; color:var(--ink); background:#f5f7f2; font-family:"PingFang SC","Microsoft YaHei",sans-serif; max-width:1440px; margin:0 auto; min-height:100vh; box-sizing:border-box }
.travel *{box-sizing:border-box}.travel button,.travel input{font:inherit}.travel button{cursor:pointer}.travel button:disabled{cursor:not-allowed;opacity:.5}.travel button:focus-visible,.travel input:focus-visible{outline:3px solid #85b5a1;outline-offset:3px}.planner,.summary,.field-block{min-width:0;min-inline-size:0}
.topbar{height:74px;padding:0 56px;display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #e9eee8}.wordmark{display:flex;align-items:center;gap:16px}.wordmark strong{font-size:18px;letter-spacing:.05em}.wordmark span{border-left:1px solid #e3eae2;padding-left:16px;color:#84938b;font-size:12px}.destination{font-size:12px;color:#64776e;display:flex;align-items:center;gap:8px}.location-dot{width:7px;height:7px;border-radius:50%;background:#80ae90;display:inline-block;flex:none}
.workspace{padding:0 56px 70px}.page-intro{display:flex;align-items:end;justify-content:space-between;gap:24px;margin:52px 0 30px}.eyebrow{font-size:12px;letter-spacing:.08em;color:#658477;margin:0 0 11px;font-weight:600}.page-intro h1{font-size:36px;line-height:1.3;margin:0 0 12px;letter-spacing:.01em;font-weight:700}.page-intro>div>p:not(.eyebrow),.discover-head p:not(.eyebrow){font-size:14px;color:var(--muted);margin:0;line-height:1.8}.intro-note{display:flex;flex-direction:column;gap:5px;min-width:90px;padding-left:18px;border-left:1px solid #dce7db}.intro-note span{font-size:11px;color:#91a299}.intro-note strong{font-size:15px}
.workspace-grid{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:20px;align-items:stretch}.planner{background:#fff;border:1px solid var(--line);border-radius:14px;padding:32px 34px}.panel-heading{display:flex;justify-content:space-between;gap:16px;align-items:start}.panel-heading h2,.discover h2{font-size:22px;margin:0 0 8px;line-height:1.4}.panel-heading p{font-size:13px;line-height:1.7;color:var(--muted);margin:0}.step-label{background:#f3f6ef;color:#6e8577;font-size:11px;padding:7px 10px;border-radius:5px;white-space:nowrap}.planner form{margin-top:30px}.field-block{border:0;padding:0;margin:0 0 29px}.field-block legend,.field-block>label{font-size:14px;font-weight:700;margin-bottom:7px;display:block}.field-block legend span{font-size:11px;color:#94a298;font-weight:400;margin-left:8px}.field-description{font-size:12px;line-height:1.7;color:#85938b;margin:0 0 13px}
.day-options{display:flex;gap:9px;flex-wrap:wrap}.day-option{width:62px;height:50px;background:#fafbf9;border:1px solid #e5ebe3;border-radius:7px;display:flex;align-items:baseline;justify-content:center;gap:5px;color:#778980}.day-option strong{font-size:17px}.day-option span{font-size:11px}.day-option.selected{border-color:#315f51;background:#edf5ed;color:#244e41}.interest-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.interest{display:flex;align-items:start;gap:10px;text-align:left;min-width:0;min-height:76px;padding:14px 12px;background:#fafbf9;border:1px solid #e5ebe3;border-radius:8px;color:#546a5e}.interest.selected{border-color:#628d76;background:#f0f7ec;color:#264f40}.interest-indicator{display:grid;place-items:center;flex:none;width:20px;height:20px;border:1px solid #d4dfd5;border-radius:50%;font-size:13px;color:#81998b;line-height:1}.interest.selected .interest-indicator{background:#376b56;color:white;border-color:#376b56}.interest-copy{min-width:0;display:flex;flex-direction:column;gap:6px}.interest-copy strong{font-size:13px}.interest-copy small{font-size:11px;color:#899990;line-height:1.45}
.budget{margin-bottom:0}.budget-row{display:flex;align-items:stretch;gap:12px}.budget-input{display:flex;align-items:center;gap:10px;width:230px;padding:0 13px;border:1px solid #e0e8df;background:#fafbf9;border-radius:7px}.budget-input:focus-within{outline:2px solid #85b5a1;outline-offset:2px}.budget-input span{font-size:12px;color:#8c9c93;white-space:nowrap}.budget-input span:first-child{font-size:17px;color:#547364}.budget-input input{min-width:0;flex:1;border:0;outline:0;background:transparent;padding:12px 0;font-size:16px;color:var(--ink)}.budget-suggestions{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.budget-suggestions button{padding:8px 10px;border:1px solid transparent;border-radius:5px;background:transparent;font-size:12px;color:#85968b}.budget-suggestions button.active{background:#f0f5ed;border-color:#dfebda;color:#426e55}.budget>small{display:block;margin-top:9px;font-size:12px;color:#899990}.error{color:#9d4038;background:#fff1ee;padding:12px 14px;border-radius:6px;font-size:13px;line-height:1.6}.retry{color:inherit;background:transparent;border:0;text-decoration:underline}
.summary{background:#173a30;color:white;border-radius:14px;padding:29px 28px;display:flex;flex-direction:column;justify-content:space-between}.summary-top{display:flex;align-items:center;justify-content:space-between;gap:10px;color:#bdcfc5;font-size:12px}.summary-location{display:inline-flex;gap:7px;align-items:center;color:#bdcfc5;font-size:11px}.summary h2{font-size:38px;line-height:1.2;letter-spacing:.06em;font-weight:650;margin:35px 0 10px}.summary-caption{font-size:12px;line-height:1.8;color:#b8cbc0;margin:0}.summary-divider{height:1px;background:rgba(219,237,222,.15);margin:27px 0 9px}.summary-list{margin:0}.summary-list>div{display:flex;justify-content:space-between;gap:14px;padding:13px 0}.summary-list dt{font-size:12px;color:#b1c5ba}.summary-list dd{margin:0;font-size:13px;text-align:right;color:#f4fbf3}.summary-note{border-top:1px solid rgba(219,237,222,.15);padding-top:17px;margin:4px 0 24px;color:#a8beb1;font-size:11px;line-height:1.8}.summary-actions{display:grid;gap:10px}.primary-button,.secondary-button{width:100%;border-radius:6px;padding:14px 15px;font-size:13px;font-weight:700}.primary-button{display:flex;justify-content:center;align-items:center;gap:13px;border:1px solid #d9eaa7;background:#d9eaa7;color:#193e30}.primary-button:hover:not(:disabled){background:#ebf6c5}.primary-button svg{width:17px;height:17px}.secondary-button{border:1px solid rgba(225,240,228,.28);background:transparent;color:#e2eee4}.secondary-button:hover:not(:disabled){background:rgba(255,255,255,.07)}.summary-actions>p{text-align:center;color:#a8beb1;font-size:11px;line-height:1.6;margin:2px 0 0}
.discover{padding-top:58px}.discover-head{display:flex;justify-content:space-between;align-items:end;gap:24px}.discover h2{font-size:25px}.search{display:flex;align-items:center;gap:9px;min-width:225px;padding:10px 12px;border:1px solid #dfe7dc;border-radius:7px;background:white;color:#789084}.search:focus-within{outline:2px solid #85b5a1;outline-offset:2px}.search svg{width:18px;height:18px;flex:none}.search input{width:100%;border:0;outline:0;background:transparent;color:var(--ink);font-size:13px}.filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:27px 0 12px}.filters button{padding:8px 14px;border:1px solid transparent;border-radius:6px;background:transparent;color:#7a8d80;font-size:13px}.filters button.active{background:#e6eee0;color:#315d47;font-weight:650}.filter-count{margin-left:auto;font-size:12px;color:#96a59a}.places{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 26px;border-top:1px solid #dfe7dd}.place{display:flex;justify-content:space-between;gap:16px;min-height:156px;padding:20px 0;border-bottom:1px solid #dfe7dd}.place-main{min-width:0}.place-meta{display:flex;align-items:center;gap:11px;font-size:11px;color:#93a39a}.place-category{color:#53836a;font-weight:700}.place h3{font-size:16px;margin:11px 0 7px}.place p{font-size:12px;line-height:1.7;color:#778b7e;margin:0 0 7px}.place .price-note{color:#98a69c;margin:0}.place-details{display:flex;flex-direction:column;align-items:end;justify-content:center;gap:7px;flex:none;color:#83978a;font-size:11px}.place-details strong{font-size:12px;color:#567462;font-weight:600}.place-details small{font-size:10px;color:#a0aea3}.empty{padding:38px 0;color:#718581;font-size:14px}.more-button{display:block;margin:25px auto 0;padding:11px 18px;border:1px solid #d5e2d5;color:#436f58;background:transparent;border-radius:5px}.data-note{text-align:center;margin-top:28px;color:#98a89d;font-size:11px;line-height:1.8}
.reference-links{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px;font-size:12px;line-height:1.7}
.reference-links a{color:var(--accent);text-underline-offset:3px}
.summary-actions .plan-link{margin:2px 0;font-size:13px}
.plan-link a{color:#e2eee4;text-underline-offset:3px}
.reference-links a:focus-visible,.plan-link a:focus-visible{outline:2px solid #85b5a1;outline-offset:3px}
@media(max-width:950px){.topbar{padding:0 28px}.workspace{padding:0 28px 55px}.workspace-grid{grid-template-columns:minmax(0,1fr) 290px}.planner{padding:28px 24px}.interest-options{grid-template-columns:1fr}.interest{min-height:auto;align-items:center}.interest-copy{gap:2px}}
@media(max-width:680px){.topbar{height:68px;padding:0 18px}.wordmark{gap:9px}.wordmark strong{font-size:16px}.wordmark span{padding-left:9px}.workspace{padding:0 16px 38px}.page-intro{margin:34px 0 22px;align-items:start}.page-intro h1{font-size:27px}.intro-note{min-width:55px;padding-left:12px}.workspace-grid{grid-template-columns:1fr;gap:14px}.planner{padding:25px 20px}.panel-heading h2{font-size:19px}.summary{padding:25px 22px}.summary h2{margin-top:22px;font-size:30px}.summary-note{margin-bottom:18px}.budget-row{flex-wrap:wrap}.budget-input{width:100%}.discover{padding-top:42px}.discover-head{align-items:start;flex-direction:column}.discover h2{font-size:22px}.search{width:100%}.places{grid-template-columns:1fr}.place{min-height:125px}.day-option{flex:1;width:auto;min-width:0}.interest-options{grid-template-columns:1fr}.field-block{margin-bottom:25px}}
@media(prefers-reduced-motion:reduce){.travel *{transition:none!important}}
</style>
