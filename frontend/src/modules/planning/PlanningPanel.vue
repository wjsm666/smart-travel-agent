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
const form = reactive({
  city: '',
  day_count: 2 as number | undefined,
  preferences: [] as Category[],
  budget_cny: 500 as number | undefined,
})

const cities = computed(() => [...new Set(attractions.value.map((item) => item.city))].sort())
const visibleAttractions = computed(() => {
  const search = keyword.value.trim()
  return attractions.value.filter((item) => {
    return (
      (!form.city || item.city === form.city) &&
      (!categoryFilter.value || item.category === categoryFilter.value) &&
      (!search || item.name.includes(search) || item.description.includes(search))
    )
  })
})

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

async function loadCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const result = await requestJson<{ items: Attraction[] }>('/api/attractions')
    attractions.value = result.items
    emit('catalog-loaded', result.items)
    if (!cities.value.includes(form.city)) form.city = cities.value[0] ?? ''
  } catch (error) {
    catalogError.value = errorMessage(error, '景点加载失败，请稍后重试。')
  } finally {
    catalogLoading.value = false
  }
}

async function generate(mode: GenerationRequest['mode']) {
  if (generating.value) return
  generationError.value = ''
  const { city, day_count: dayCount, budget_cny: budget, preferences } = form
  if (!cities.value.includes(city)) {
    generationError.value = '请选择示例数据中已有的目的地。'
    return
  }
  if (dayCount === undefined || !Number.isInteger(dayCount) || dayCount < 1 || dayCount > 5) {
    generationError.value = '旅游天数需要填写 1 至 5 之间的整数。'
    return
  }
  if (budget === undefined || !Number.isInteger(budget) || budget < 0) {
    generationError.value = '门票预算需要填写非负整数。'
    return
  }

  generating.value = true
  try {
    const payload: GenerationRequest = {
      city,
      day_count: dayCount,
      preferences: [...preferences],
      budget_cny: budget,
      mode,
    }
    const plan = await requestJson<PlanView>('/api/plans/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    emit('plan-generated', plan)
  } catch (error) {
    generationError.value = errorMessage(error, '生成失败，请稍后重试。')
  } finally {
    generating.value = false
  }
}

onMounted(loadCatalog)
</script>

<template>
  <section class="planning-panel" aria-labelledby="planning-title">
    <div class="intro">
      <p class="eyebrow">TRAVEL PLANNER</p>
      <h2 id="planning-title">规划一段轻松的旅程</h2>
      <p>选择目的地和旅行偏好，先生成一份可以调整的行程草案。</p>
    </div>

    <el-alert
      class="notice"
      type="info"
      :closable="false"
      title="当前为课程示例数据，费用仅估算景点门票，不含交通、餐饮和住宿。"
      show-icon
    />

    <div class="panel-grid">
      <div class="form-card">
        <h3>旅行需求</h3>
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="目的地" required>
            <el-select v-model="form.city" placeholder="选择目的地" :disabled="generating || catalogLoading">
              <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
            </el-select>
          </el-form-item>
          <div class="fields">
            <el-form-item label="旅游天数" required>
              <el-input-number v-model="form.day_count" :min="1" :max="5" :precision="0" :disabled="generating" />
            </el-form-item>
            <el-form-item label="门票预算（元）" required>
              <el-input-number v-model="form.budget_cny" :min="0" :precision="0" :disabled="generating" />
            </el-form-item>
          </div>
          <el-form-item label="兴趣偏好">
            <el-select v-model="form.preferences" multiple placeholder="可多选，也可以不选" :disabled="generating">
              <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
            </el-select>
          </el-form-item>
          <el-alert v-if="generationError" class="notice" type="error" :title="generationError" :closable="false" show-icon />
          <div class="actions">
            <el-button type="primary" :loading="generating" :disabled="catalogLoading || !cities.length" @click="generate('agent')">
              AI 推荐
            </el-button>
            <el-button :disabled="generating || catalogLoading || !cities.length" @click="generate('rules')">
              规则推荐
            </el-button>
          </div>
          <p class="hint">AI 不可用时，可主动选择规则推荐。草案需要确认后才会保存。</p>
        </el-form>
      </div>

      <div class="catalog-card">
        <div class="catalog-heading">
          <div>
            <h3>看看有哪些景点</h3>
            <p class="hint">以下均为虚构的示例景点。</p>
          </div>
          <el-button text :loading="catalogLoading" :disabled="generating" @click="loadCatalog">刷新</el-button>
        </div>
        <el-alert v-if="catalogError" class="notice" type="error" :title="catalogError" :closable="false" show-icon />
        <div class="filters">
          <el-input v-model="keyword" placeholder="搜索景点名称或简介" clearable aria-label="搜索景点" />
          <el-select v-model="categoryFilter" placeholder="全部类别" clearable aria-label="筛选景点类别">
            <el-option v-for="category in categories" :key="category" :label="category" :value="category" />
          </el-select>
        </div>
        <div v-loading="catalogLoading" class="attractions">
          <el-empty v-if="!catalogLoading && !visibleAttractions.length" description="没有找到符合条件的景点" :image-size="72" />
          <article v-for="item in visibleAttractions" :key="item.id" class="attraction">
            <div>
              <h4>{{ item.name }}</h4>
              <p>{{ item.description }}</p>
            </div>
            <div class="attraction-meta">
              <el-tag size="small" effect="light">{{ item.category }}</el-tag>
              <span>参考门票 ¥{{ item.ticket_cny }}</span>
            </div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.planning-panel { color: #243334; }
.intro { margin-bottom: 20px; }
.intro h2, .catalog-heading h3, .form-card h3 { margin: 0 0 8px; }
.intro p, .hint { color: #66777a; margin: 0; line-height: 1.6; }
.intro .eyebrow { color: #237c70; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; margin-bottom: 6px; }
.notice { margin-bottom: 18px; }
.panel-grid { display: grid; grid-template-columns: minmax(260px, 0.8fr) minmax(320px, 1.2fr); gap: 18px; }
.form-card, .catalog-card { padding: 22px; border: 1px solid #e4eeeb; border-radius: 14px; background: #fff; }
.form-card :deep(.el-select), .form-card :deep(.el-input-number) { width: 100%; }
.fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.actions { display: flex; gap: 8px; margin-bottom: 10px; }
.hint { font-size: 13px; }
.catalog-heading { display: flex; justify-content: space-between; align-items: start; gap: 12px; margin-bottom: 15px; }
.filters { display: grid; grid-template-columns: 1fr 120px; gap: 10px; margin-bottom: 12px; }
.attractions { min-height: 120px; max-height: 470px; overflow-y: auto; }
.attraction { display: flex; justify-content: space-between; gap: 12px; padding: 14px 2px; border-bottom: 1px solid #eef3f1; }
.attraction:last-child { border-bottom: 0; }
.attraction h4, .attraction p { margin: 0; }
.attraction p { color: #718083; font-size: 13px; margin-top: 5px; }
.attraction-meta { display: flex; flex-direction: column; align-items: end; gap: 7px; white-space: nowrap; font-size: 13px; color: #526466; }
@media (max-width: 760px) { .panel-grid { grid-template-columns: 1fr; } }
@media (max-width: 420px) { .fields, .filters { grid-template-columns: 1fr; } .attraction { flex-direction: column; } .attraction-meta { flex-direction: row; align-items: center; } }
</style>
