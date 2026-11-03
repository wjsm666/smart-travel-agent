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
    <header class="travel-header">
      <div class="brand"><span class="brand-seal" aria-hidden="true">汕</span><span><strong>漫游汕头</strong><small>一份慢慢走的城市指南</small></span></div>
      <span class="header-place">广东 · 汕头</span>
    </header>

    <div class="hero">
      <div class="hero-copy">
        <span class="hero-kicker">山海之间，老城之上</span>
        <h1 id="planning-title">去汕头，<br>留点时间给<span>海。</span></h1>
        <p>从骑楼老街到海岛日落，告诉我们你的喜好，一起把这趟旅程慢慢排好。</p>
        <div class="hero-foot"><span class="sun-dot"></span><span>为你的汕头之行，做一份轻盈的计划</span></div>
      </div>
      <div class="postcard" role="img" aria-label="汕头滨海和骑楼风格的插画">
        <svg viewBox="0 0 540 430" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="540" height="430" fill="#B8D5D6"/><circle cx="397" cy="99" r="53" fill="#F4CE92"/>
          <path d="M0 270C80 241 159 256 229 244C325 227 413 251 540 219V430H0V270Z" fill="#638E93"/>
          <path d="M0 313C94 286 153 306 249 290C341 274 422 300 540 270V430H0V313Z" fill="#39717A"/>
          <path d="M0 350C106 330 167 341 264 329C369 316 441 333 540 319V430H0V350Z" fill="#204D60"/>
          <path d="M30 258H316V277H30V258Z" fill="#E4CFB1"/><path d="M51 157H292V257H51V157Z" fill="#F1E2C8"/>
          <path d="M42 151L171 106L302 151V162H42V151Z" fill="#D68B68"/><path d="M59 148L171 119L284 148" stroke="#8D5E51" stroke-width="4"/>
          <path d="M79 168H121V257H79V168ZM151 168H193V257H151V168ZM223 168H265V257H223V168Z" fill="#C4A88F"/>
          <path d="M85 197C85 186 94 177 105 177C116 177 125 186 125 197V257H85V197ZM151 197C151 186 160 177 171 177C182 177 191 186 191 197V257H151V197ZM217 197C217 186 226 177 237 177C248 177 257 186 257 197V257H217V197Z" fill="#52747A"/>
          <path d="M75 257H267M171 105V85M149 88H193" stroke="#835E50" stroke-width="5"/>
          <path d="M339 276L395 257L434 270L397 284L339 276Z" fill="#E9D6B5"/><path d="M390 257V207L361 253L390 257Z" fill="#EEDCC2"/><path d="M391 203V257" stroke="#EEDCC2" stroke-width="4"/>
          <path d="M78 343C118 337 149 338 180 342M320 365C370 356 413 359 451 364M72 382C103 377 135 379 156 381" stroke="#AEC8C1" stroke-width="3" stroke-linecap="round" opacity=".6"/>
          <path d="M79 64C90 55 101 55 112 64M119 74C127 68 135 68 143 74" stroke="#547F83" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <span class="postcard-caption">一湾山海，一城烟火</span>
      </div>
    </div>

    <div class="content-grid">
      <section class="planner" aria-labelledby="form-title">
        <div class="section-heading"><div><span class="section-label">开始规划</span><h2 id="form-title">你的旅行，按你的节奏</h2></div><span class="place-chip">汕头</span></div>
        <p class="section-intro">告诉我们计划停留多久，以及想遇见什么样的风景。</p>
        <form @submit.prevent="generate('agent')">
          <div class="input-grid">
            <div class="field"><label for="trip-days">游玩天数</label><div class="input-wrap"><input id="trip-days" v-model.number="form.day_count" type="number" min="1" max="5" step="1" :disabled="generating"><span>天</span></div><small>支持 1–5 天</small></div>
            <div class="field"><label for="trip-budget">门票预算</label><div class="input-wrap"><input id="trip-budget" v-model.number="form.budget_cny" type="number" min="0" step="1" :disabled="generating"><span>元 / 人</span></div><small>不含交通、餐饮与住宿</small></div>
          </div>
          <fieldset class="interests"><legend>旅行偏好 <span>可多选</span></legend><div class="interest-options"><button v-for="category in categories" :key="category" type="button" class="interest" :class="{ selected: form.preferences.includes(category) }" :aria-pressed="form.preferences.includes(category)" :disabled="generating" @click="togglePreference(category)"><span class="interest-mark" aria-hidden="true">{{ category === '自然' ? '◒' : category === '人文' ? '⌂' : '✳' }}</span>{{ category }}</button></div></fieldset>
          <p v-if="generationError" class="error" role="alert">{{ generationError }}</p>
          <div class="actions"><button class="primary-button" type="submit" :disabled="generating || catalogLoading || !attractions.length">{{ generating ? '正在规划…' : '生成我的行程' }} <span aria-hidden="true">↗</span></button><button class="secondary-button" type="button" :disabled="generating || catalogLoading || !attractions.length" @click="generate('rules')">使用规则推荐</button></div>
          <p class="form-note">行程生成后可以继续调整，确认后才会保存。</p>
        </form>
      </section>

      <aside class="travel-note"><div class="note-icon" aria-hidden="true">✺</div><div><span class="section-label">出发前的小提醒</span><h3>留白，也是一种旅行</h3><p>海岛和市区之间建议预留充裕时间。门票为人工整理的参考信息，实际开放及费用请以景区为准。</p><div class="note-stamp">潮汕 · 慢游</div></div></aside>
    </div>

    <section class="discover" aria-labelledby="discover-title">
      <div class="discover-head"><div><span class="section-label">认识这座城市</span><h2 id="discover-title">先看看，想去哪里</h2><p>从老城街巷到海边山色，挑一处你喜欢的风景。</p></div><label class="search"><span aria-hidden="true">⌕</span><input v-model="keyword" type="search" placeholder="搜索景点" aria-label="搜索景点"></label></div>
      <div class="filters" role="group" aria-label="筛选景点类别"><button type="button" :class="{ active: !categoryFilter }" :aria-pressed="!categoryFilter" @click="chooseFilter('')">全部</button><button v-for="category in categories" :key="category" type="button" :class="{ active: categoryFilter === category }" :aria-pressed="categoryFilter === category" @click="chooseFilter(category)">{{ category }}</button><span class="filter-count">{{ filteredAttractions.length }} 处景点</span></div>
      <p v-if="catalogError" class="error" role="alert">{{ catalogError }} <button type="button" class="retry" @click="loadCatalog">重新加载</button></p>
      <p v-else-if="catalogLoading" class="empty" role="status">正在加载景点资料…</p>
      <p v-else-if="!filteredAttractions.length" class="empty">没有找到符合条件的景点，换个关键词试试。</p>
      <div v-else class="places"><article v-for="item in visibleAttractions" :key="item.id" class="place"><div class="place-top"><span class="place-category">{{ item.category }}</span><span class="place-area">{{ item.area || '汕头' }}</span></div><h3>{{ item.name }}</h3><p>{{ item.description }}</p><p v-if="item.ticket_note" class="price-note">{{ item.ticket_note }}</p><div class="place-bottom"><span>{{ item.duration_min ? `建议 ${Math.round(item.duration_min / 6) / 10} 小时` : '时长待确认' }}</span><span class="price">{{ ticketLabel(item) }}<small v-if="item.ticket_checked_at">核对于 {{ item.ticket_checked_at }}</small></span></div></article></div>
      <button v-if="filteredAttractions.length > 6" class="more-button" type="button" @click="showAll = !showAll">{{ showAll ? '收起景点' : `查看更多景点（${filteredAttractions.length - 6}）` }}</button>
      <div class="data-note">景点资料为人工整理，仅供行程规划参考。票价、开放状态和交通请在出发前核实。</div>
    </section>
  </section>
</template>

<style scoped>
.travel{--ink:#183746;--muted:#60747a;--sea:#286a72;--pale:#e5efed;--line:#d6e2df;--paper:#f6f9f6;color:var(--ink);background:var(--paper);font-family:"Microsoft YaHei","PingFang SC",sans-serif;max-width:1440px;margin:0 auto;padding:0 48px 64px;box-sizing:border-box}
.travel *{box-sizing:border-box}.travel button,.travel input{font:inherit}.travel button{cursor:pointer}.travel button:disabled{cursor:not-allowed;opacity:.55}.travel button:focus-visible,.travel input:focus-visible{outline:3px solid #d1945e;outline-offset:3px}
.travel-header{height:82px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:12px}.brand-seal{display:grid;place-items:center;width:41px;height:41px;background:var(--sea);color:white;font-family:serif;font-size:22px;border-radius:50%}.brand strong,.brand small{display:block}.brand strong{font-size:17px;letter-spacing:.1em}.brand small{font-size:11px;color:var(--muted);margin-top:4px;letter-spacing:.08em}.header-place{font-size:13px;color:var(--muted)}
.hero{display:grid;grid-template-columns:1fr 1fr;min-height:400px;margin-top:24px;background:#dbe9e6;border-radius:6px;overflow:hidden}.hero-copy{padding:60px 24px 45px 7%;display:flex;flex-direction:column;align-items:flex-start}.hero-kicker,.section-label{font-size:12px;font-weight:700;color:var(--sea);letter-spacing:.1em}.hero h1{font-family:"Songti SC","SimSun",serif;font-size:clamp(38px,4.2vw,62px);line-height:1.26;letter-spacing:.04em;margin:20px 0;color:#183f4c}.hero h1 span{color:#c0784c}.hero-copy>p{font-size:15px;line-height:1.9;max-width:370px;color:#536e70;margin:0}.hero-foot{display:flex;align-items:center;gap:10px;margin-top:auto;padding-top:35px;color:#60797a;font-size:12px}.sun-dot{height:9px;width:9px;border-radius:50%;background:#d58b53}.postcard{position:relative;min-height:380px;overflow:hidden}.postcard svg{width:100%;height:100%;position:absolute;inset:0;object-fit:cover}.postcard-caption{position:absolute;bottom:22px;right:24px;font-family:serif;font-size:13px;color:#fff;letter-spacing:.15em}
.content-grid{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:48px;padding:50px 0 48px;border-bottom:1px solid var(--line)}.section-heading{display:flex;justify-content:space-between;align-items:start;gap:16px}.section-heading h2,.discover h2{font-family:"Songti SC","SimSun",serif;font-size:27px;line-height:1.3;margin:10px 0}.place-chip{background:#dcebe7;color:#326e6e;border-radius:3px;padding:7px 13px;font-size:12px}.section-intro,.discover-head p{font-size:13px;line-height:1.8;color:var(--muted);margin:0 0 24px}.input-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.field label,.interests legend{font-size:13px;font-weight:700;display:block;margin-bottom:9px}.input-wrap{display:flex;align-items:center;border:1px solid #cbdcd8;background:white;border-radius:4px;padding:0 14px}.input-wrap input{width:100%;min-width:0;border:0;outline:0;background:transparent;padding:13px 0;color:var(--ink);font-size:17px}.input-wrap span{font-size:12px;color:var(--muted);white-space:nowrap}.input-wrap:focus-within{outline:2px solid #d1945e;outline-offset:2px}.field small{display:block;margin-top:7px;font-size:11px;color:#748887}.interests{border:0;padding:0;margin:25px 0 0}.interests legend span{font-weight:400;color:#839493;margin-left:6px}.interest-options{display:flex;gap:10px;flex-wrap:wrap}.interest{border:1px solid #cfdfdb;color:#546e70;background:transparent;border-radius:4px;padding:10px 17px;transition:background .15s,border-color .15s}.interest.selected{border-color:var(--sea);background:#dcebe7;color:#1f6267}.interest-mark{margin-right:8px}.actions{display:flex;gap:12px;margin-top:30px;flex-wrap:wrap}.primary-button,.secondary-button{border-radius:4px;padding:14px 22px;font-weight:700;font-size:14px}.primary-button{background:#245d65;color:white;border:1px solid #245d65;min-width:190px;display:flex;justify-content:space-between;gap:20px}.primary-button:hover:not(:disabled){background:#194c55}.secondary-button{background:transparent;border:1px solid #c5d6d2;color:#355d60}.form-note{font-size:12px;color:#718582;margin:12px 0 0}.error{color:#a74837;background:#fff3ed;padding:12px 14px;border-radius:4px;line-height:1.5;font-size:13px}.retry{background:transparent;border:0;color:inherit;text-decoration:underline}.travel-note{background:#edf2e9;padding:24px 22px;align-self:start;display:flex;gap:14px;min-height:220px}.note-icon{font-size:28px;color:#b2774b;line-height:1}.travel-note h3{font-family:"Songti SC","SimSun",serif;font-size:19px;margin:11px 0}.travel-note p{font-size:12px;color:#71827a;line-height:1.9;margin:0}.note-stamp{color:#9b704f;font-family:serif;font-size:12px;margin-top:22px;letter-spacing:.12em}
.discover{padding-top:48px}.discover-head{display:flex;justify-content:space-between;gap:20px;align-items:end}.discover-head p{margin-bottom:0}.search{display:flex;align-items:center;gap:8px;border-bottom:1px solid #9fb7b3;padding:8px 0;min-width:210px;color:#4e7778}.search span{font-size:22px}.search input{width:100%;border:0;background:transparent;outline:0;color:var(--ink);font-size:13px}.search:focus-within{outline:2px solid #d1945e;outline-offset:4px}.filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:28px 0 18px}.filters button{background:transparent;border:1px solid transparent;padding:8px 15px;border-radius:20px;color:#718683;font-size:13px}.filters button.active{background:#286a72;color:white}.filter-count{margin-left:auto;font-size:12px;color:#81918f}.places{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.place{background:white;border:1px solid #e3ece9;padding:21px 20px 18px;min-height:174px;display:flex;flex-direction:column}.place-top,.place-bottom{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:12px;color:#536c67}.place-category{color:#337778;background:#e6f1ed;padding:5px 9px}.place-area{color:#617772}.place h3{font-family:"Songti SC","SimSun",serif;font-size:18px;margin:16px 0 7px}.place p{font-size:12px;line-height:1.7;color:#536b66;margin:0 0 12px}.place .price-note{color:#667a75;margin-bottom:14px}.place-bottom{margin-top:auto;border-top:1px solid #edf2ef;padding-top:12px}.price{text-align:right}.price small{display:block;margin-top:3px;color:#667a75}.empty{padding:38px 0;color:#718581;font-size:14px}.more-button{margin:24px auto 0;display:block;padding:11px 20px;background:transparent;color:#326d70;border:1px solid #bfd2cd;border-radius:4px}.data-note{text-align:center;color:#627772;font-size:12px;line-height:1.7;margin-top:28px}
@media(max-width:900px){.travel{padding:0 24px 48px}.hero-copy{padding-left:8%}.content-grid{grid-template-columns:1fr;gap:25px}.travel-note{min-height:0}.places{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.travel{padding:0 16px 38px}.travel-header{height:70px}.header-place{font-size:12px}.hero{grid-template-columns:1fr;margin-top:15px}.hero-copy{padding:36px 24px 25px}.hero h1{font-size:clamp(30px,8.2vw,36px);margin:15px 0}.hero-foot{padding-top:22px}.postcard{min-height:230px}.content-grid{padding:37px 0;gap:25px}.input-grid{gap:10px}.section-heading h2,.discover h2{font-size:23px}.discover{padding-top:36px}.discover-head{align-items:start;flex-direction:column}.search{width:100%}.places{grid-template-columns:1fr}.place{min-height:145px}.actions{gap:8px}.primary-button{min-width:0;flex:1}.secondary-button{padding:14px 13px}}
@media(prefers-reduced-motion:reduce){.travel *{transition:none!important}}
</style>
