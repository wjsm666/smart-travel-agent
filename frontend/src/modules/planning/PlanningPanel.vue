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
const generating = ref(false)
const catalogError = ref('')
const generationError = ref('')
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
  generating.value = true
  try {
    const payload: GenerationRequest = { ...form, preferences: [...form.preferences], mode }
    const plan = await requestJson<PlanView>('/api/plans/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    })
    emit('plan-generated', plan)
  } catch (error) {
    generationError.value = errorMessage(error, '行程暂时无法生成，请稍后重试。')
  } finally {
    generating.value = false
  }
}
onMounted(loadCatalog)
</script>

<template>
  <section class="travel" aria-labelledby="planning-title">
    <header class="app-header">
      <div class="brand"><span class="brand-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M3 10.5c2.2 0 2.2-2 4.5-2s2.2 2 4.5 2 2.2-2 4.5-2 2.2 2 4.5 2M3 15.5c2.2 0 2.2-2 4.5-2s2.2 2 4.5 2 2.2-2 4.5-2 2.2 2 4.5 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></span><span><strong>汕头行程</strong><small>城市旅行规划</small></span></div>
      <div class="location"><span class="location-dot"></span>广东 · 汕头</div>
    </header>

    <div class="hero">
      <div class="hero-copy"><div class="hero-tag"><span></span>目的地：汕头</div><h1 id="planning-title">你的汕头行程，<br>从这里开始。</h1><p>选好天数、预算和旅行偏好，生成一份属于你的行程。山海、老城与街巷，慢慢探索。</p><div class="hero-meta"><span>汕头景点参考资料</span><span>·</span><span>行程可调整</span></div></div>
      <div class="hero-art" role="img" aria-label="汕头海岸线路示意插画"><svg viewBox="0 0 520 280" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M520 0H281C239 25 241 58 198 74C161 88 145 116 166 138C193 168 173 193 134 201C95 209 80 244 53 280H520V0Z" fill="#1D5AA8"/><path d="M520 0H324C292 30 305 64 266 83C229 102 215 120 230 145C247 173 227 195 196 206C164 217 158 245 142 280H520V0Z" fill="#2471CA"/><path d="M0 71C84 80 117 49 171 58M23 115C86 121 125 104 147 89M44 158C98 158 117 147 131 133" stroke="#75A8D8" stroke-width="1.5" opacity=".48"/><path d="M204 227C237 197 253 203 271 176C291 145 320 154 343 121C360 97 383 92 406 76" stroke="#A7E8E6" stroke-width="3" stroke-dasharray="6 8" stroke-linecap="round"/><circle cx="204" cy="227" r="7" fill="#C6F5EC"/><circle cx="271" cy="176" r="7" fill="#C6F5EC"/><circle cx="343" cy="121" r="7" fill="#C6F5EC"/><circle cx="406" cy="76" r="7" fill="#C6F5EC"/><circle cx="406" cy="76" r="16" stroke="#C6F5EC" stroke-opacity=".5" stroke-width="2"/><path d="M343 28V11M335 20H351" stroke="#A4DBE2" stroke-width="2" stroke-linecap="round"/><path d="M101 247H65M83 229V265" stroke="#7BB8D9" stroke-width="1.5" opacity=".5"/></svg></div>
    </div>

    <div class="content-grid">
      <section class="planner" aria-labelledby="form-title">
        <div class="section-heading"><div><div class="section-eyebrow">开始规划</div><h2 id="form-title">告诉我们你的旅行计划</h2><p>填写基本条件，生成后还可以继续调整。</p></div><span class="place-chip">汕头</span></div>
        <form @submit.prevent="generate('agent')">
          <div class="input-grid"><div class="field"><label for="trip-days">游玩天数</label><div class="input-wrap"><input id="trip-days" v-model.number="form.day_count" type="number" min="1" max="5" step="1" :disabled="generating"><span>天</span></div><small>支持 1–5 天</small></div><div class="field"><label for="trip-budget">门票预算</label><div class="input-wrap"><input id="trip-budget" v-model.number="form.budget_cny" type="number" min="0" step="1" :disabled="generating"><span>元 / 人</span></div><small>不含交通、餐饮与住宿</small></div></div>
          <fieldset class="interests"><legend>旅行偏好 <span>可多选</span></legend><div class="interest-options"><button v-for="category in categories" :key="category" type="button" class="interest" :class="{ selected: form.preferences.includes(category) }" :aria-pressed="form.preferences.includes(category)" :disabled="generating" @click="togglePreference(category)"><span class="check" aria-hidden="true">{{ form.preferences.includes(category) ? '✓' : '+' }}</span>{{ category }}</button></div></fieldset>
          <p v-if="generationError" class="error" role="alert">{{ generationError }}</p>
          <div class="actions"><button class="primary-button" type="submit" :disabled="generating || catalogLoading || !attractions.length">{{ generating ? '正在规划…' : '生成我的行程' }}</button><button class="secondary-button" type="button" :disabled="generating || catalogLoading || !attractions.length" @click="generate('rules')">使用规则推荐</button></div><p class="form-note">生成后可修改景点，确认后才会保存。</p>
        </form>
      </section>

      <aside class="travel-note"><div class="note-heading"><span class="note-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8"/><path d="M12 10.5V16M12 7.5v.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></span><h3>出发前了解一下</h3></div><ul><li>南澳与市区间需预留跨海交通时间。</li><li>门票为人工整理的参考值，未知价格会单独提示。</li><li>开放时间、交通和实际费用请在出发前核实。</li></ul></aside>
    </div>

    <section class="discover" aria-labelledby="discover-title"><div class="discover-head"><div><div class="section-eyebrow">探索汕头</div><h2 id="discover-title">挑选想去的地方</h2><p>按兴趣浏览，或搜索你已经想去的景点。</p></div><label class="search"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.3" stroke="currentColor" stroke-width="1.8"/><path d="m16 16 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg><input v-model="keyword" type="search" placeholder="搜索景点" aria-label="搜索景点"></label></div>
      <div class="filters" role="group" aria-label="筛选景点类别"><button type="button" :class="{ active: !categoryFilter }" :aria-pressed="!categoryFilter" @click="chooseFilter('')">全部</button><button v-for="category in categories" :key="category" type="button" :class="{ active: categoryFilter === category }" :aria-pressed="categoryFilter === category" @click="chooseFilter(category)">{{ category }}</button><span class="filter-count">{{ filteredAttractions.length }} 处景点</span></div>
      <p v-if="catalogError" class="error" role="alert">{{ catalogError }} <button type="button" class="retry" @click="loadCatalog">重新加载</button></p><p v-else-if="catalogLoading" class="empty" role="status">正在加载景点资料…</p><p v-else-if="!filteredAttractions.length" class="empty">没有找到符合条件的景点，换个关键词试试。</p>
      <div v-else class="places"><article v-for="item in visibleAttractions" :key="item.id" class="place"><div class="place-top"><span class="place-category">{{ item.category }}</span><span class="place-area">{{ item.area || '汕头' }}</span></div><h3>{{ item.name }}</h3><p>{{ item.description }}</p><p v-if="item.ticket_note" class="price-note">{{ item.ticket_note }}</p><div class="place-bottom"><span>{{ item.duration_min ? `建议 ${Math.round(item.duration_min / 6) / 10} 小时` : '时长待确认' }}</span><span class="price">{{ ticketLabel(item) }}<small v-if="item.ticket_checked_at">核对于 {{ item.ticket_checked_at }}</small></span></div></article></div>
      <button v-if="filteredAttractions.length > 6" class="more-button" type="button" @click="showAll = !showAll">{{ showAll ? '收起景点' : `查看更多景点（${filteredAttractions.length - 6}）` }}</button><div class="data-note">景点资料为人工整理，仅供行程规划参考。票价、开放状态和交通请在出发前核实。</div>
    </section>
  </section>
</template>

<style scoped>
.travel{--ink:#172e4b;--muted:#5c7189;--blue:#1769dc;--line:#dbe5f0;--surface:#fff;color:var(--ink);background:#f3f7fc;font-family:"Microsoft YaHei","PingFang SC",sans-serif;max-width:1440px;margin:0 auto;padding:0 48px 64px;box-sizing:border-box}
.travel *{box-sizing:border-box}.travel button,.travel input{font:inherit}.travel button{cursor:pointer}.travel button:disabled{cursor:not-allowed;opacity:.55}.travel button:focus-visible,.travel input:focus-visible{outline:3px solid #5699ef;outline-offset:3px}
.app-header{height:78px;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:11px}.brand-icon{display:grid;place-items:center;width:42px;height:42px;background:#1769dc;color:white;border-radius:12px}.brand-icon svg{width:25px;height:25px}.brand strong,.brand small{display:block}.brand strong{font-size:16px;letter-spacing:.02em}.brand small{font-size:11px;color:var(--muted);margin-top:3px}.location{display:flex;align-items:center;gap:7px;color:#526d89;background:white;border:1px solid #dfe8f3;border-radius:20px;padding:8px 12px;font-size:12px}.location-dot,.hero-tag span{width:7px;height:7px;border-radius:50%;background:#32b8ae}
.hero{position:relative;display:grid;grid-template-columns:1fr 1fr;min-height:330px;background:#113d76;color:#fff;border-radius:18px;overflow:hidden}.hero-copy{z-index:1;padding:48px 10px 42px 50px}.hero-tag{display:inline-flex;align-items:center;gap:8px;padding:7px 10px;border:1px solid #7597bc;border-radius:20px;color:#d7ebff;font-size:12px}.hero h1{font-size:clamp(31px,3.1vw,46px);line-height:1.35;letter-spacing:.01em;margin:19px 0 14px;color:#fff}.hero-copy>p{font-size:14px;line-height:1.9;max-width:410px;color:#d3e5f6;margin:0}.hero-meta{display:flex;align-items:center;gap:9px;color:#c1d9ef;font-size:12px;margin-top:25px}.hero-art{position:relative;min-height:290px}.hero-art svg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.content-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:20px;margin-top:24px}.planner,.travel-note{background:var(--surface);border:1px solid var(--line);border-radius:14px}.planner{padding:28px 30px 26px}.section-heading{display:flex;justify-content:space-between;gap:16px;align-items:start}.section-eyebrow{font-size:12px;font-weight:700;color:var(--blue)}.section-heading h2,.discover h2{font-size:22px;line-height:1.4;margin:8px 0;color:var(--ink)}.section-heading p,.discover-head p{font-size:13px;line-height:1.7;color:var(--muted);margin:0}.place-chip{background:#eaf2ff;color:#2368c4;border-radius:7px;padding:7px 11px;font-size:12px;white-space:nowrap}.planner form{margin-top:25px}.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.field label,.interests legend{font-size:13px;font-weight:700;display:block;margin-bottom:9px}.input-wrap{display:flex;align-items:center;border:1px solid #cfdceb;background:white;border-radius:8px;padding:0 12px}.input-wrap input{width:100%;min-width:0;border:0;outline:0;background:transparent;padding:12px 0;color:var(--ink);font-size:16px}.input-wrap span{font-size:12px;color:var(--muted);white-space:nowrap}.input-wrap:focus-within{outline:2px solid #5699ef;outline-offset:2px}.field small{display:block;margin-top:7px;font-size:12px;color:#73869a}.interests{border:0;padding:0;margin:24px 0 0}.interests legend span{font-weight:400;color:#7d8d9d;margin-left:6px}.interest-options{display:flex;gap:9px;flex-wrap:wrap}.interest{border:1px solid #cedbec;color:#536b85;background:white;border-radius:8px;padding:9px 15px;transition:background .15s,border-color .15s}.interest.selected{border-color:#347fe2;background:#edf5ff;color:#165cbd}.check{display:inline-block;width:14px;color:#5682b3;font-size:15px;margin-right:5px}.actions{display:flex;gap:12px;margin-top:25px;flex-wrap:wrap}.primary-button,.secondary-button{border-radius:8px;padding:13px 20px;font-weight:700;font-size:14px}.primary-button{background:#1769dc;color:white;border:1px solid #1769dc;min-width:174px}.primary-button:hover:not(:disabled){background:#1259c0}.secondary-button{background:white;border:1px solid #cbd9e9;color:#41617f}.form-note{font-size:12px;color:#72869a;margin:12px 0 0}.error{color:#a33d39;background:#fff1ee;padding:12px 14px;border-radius:8px;line-height:1.5;font-size:13px}.retry{background:transparent;border:0;color:inherit;text-decoration:underline}
.travel-note{padding:24px;align-self:start}.note-heading{display:flex;align-items:center;gap:10px}.note-icon{display:grid;place-items:center;width:34px;height:34px;background:#eaf3ff;color:#246bd1;border-radius:10px;flex:none}.note-icon svg{width:20px;height:20px}.travel-note h3{font-size:15px;margin:0}.travel-note ul{list-style:none;margin:16px 0 0;padding:0}.travel-note li{position:relative;padding-left:14px;color:#5e748b;font-size:12px;line-height:1.8;margin-top:11px}.travel-note li:before{content:'';position:absolute;left:0;top:.75em;width:5px;height:5px;background:#7ba6da;border-radius:50%}
.discover{padding-top:48px}.discover-head{display:flex;justify-content:space-between;gap:20px;align-items:end}.search{display:flex;align-items:center;gap:8px;background:white;border:1px solid #d7e3f0;border-radius:8px;padding:10px 12px;min-width:220px;color:#6e89a4}.search svg{width:18px;height:18px;flex:none}.search input{width:100%;border:0;background:transparent;outline:0;color:var(--ink);font-size:13px}.search:focus-within{outline:2px solid #5699ef;outline-offset:2px}.filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:24px 0 16px}.filters button{background:transparent;border:1px solid transparent;padding:8px 15px;border-radius:8px;color:#5e7690;font-size:13px}.filters button.active{background:#dfeeff;color:#125cbe;font-weight:700}.filter-count{margin-left:auto;font-size:12px;color:#73879b}.places{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.place{background:white;border:1px solid #dfe8f3;border-radius:12px;padding:19px 19px 16px;min-height:185px;display:flex;flex-direction:column}.place-top,.place-bottom{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:12px;color:#5c748e}.place-category{color:#2468c3;background:#eaf3ff;border-radius:5px;padding:5px 8px}.place-area{color:#6d8094}.place h3{font-size:17px;margin:16px 0 7px}.place p{font-size:12px;line-height:1.7;color:#5c7187;margin:0 0 12px}.place .price-note{color:#71859a;margin-bottom:14px}.place-bottom{margin-top:auto;border-top:1px solid #edf2f7;padding-top:12px}.price{text-align:right}.price small{display:block;margin-top:3px;color:#72859b}.empty{padding:38px 0;color:#71859a;font-size:14px}.more-button{margin:24px auto 0;display:block;padding:11px 20px;background:white;color:#2469c6;border:1px solid #cbdbee;border-radius:8px}.data-note{text-align:center;color:#72869b;font-size:12px;line-height:1.7;margin-top:28px}
@media(max-width:900px){.travel{padding:0 24px 48px}.content-grid{grid-template-columns:1fr;gap:16px}.places{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.travel{padding:0 16px 38px}.app-header{height:70px}.hero{grid-template-columns:1fr}.hero-copy{padding:30px 24px 8px}.hero h1{font-size:32px}.hero-art{min-height:180px}.content-grid{gap:12px;margin-top:16px}.planner{padding:23px 18px}.input-grid{gap:10px}.section-heading h2,.discover h2{font-size:20px}.discover{padding-top:36px}.discover-head{align-items:start;flex-direction:column}.search{width:100%}.places{grid-template-columns:1fr}.place{min-height:145px}.actions{gap:8px}.primary-button{min-width:0;flex:1}.secondary-button{padding:13px}}
@media(prefers-reduced-motion:reduce){.travel *{transition:none!important}}
</style>
