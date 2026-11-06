<script setup lang="ts">
import { ref, shallowRef } from 'vue'
import { ElButton, ElDialog } from 'element-plus'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/dialog/style/css'
import PlanningPanel from './modules/planning/PlanningPanel.vue'
import TripWorkspace from './modules/trips/TripWorkspace.vue'
import type { Attraction, PlanView } from './types/contracts'

const attractions = ref<Attraction[]>([])
const draft = shallowRef<PlanView | null>(null)
const pendingDraft = shallowRef<PlanView | null>(null)
const workspace = ref<InstanceType<typeof TripWorkspace> | null>(null)
const replaceOpen = ref(false)

function receivePlan(plan: PlanView) {
  if (workspace.value?.hasUnsavedChanges) {
    pendingDraft.value = plan
    replaceOpen.value = true
  } else draft.value = plan
}

function replaceDraft() {
  if (pendingDraft.value) draft.value = pendingDraft.value
  replaceOpen.value = false
  pendingDraft.value = null
}

function keepDraft() {
  replaceOpen.value = false
  pendingDraft.value = null
}
</script>

<template>
  <main>
    <PlanningPanel @catalog-loaded="attractions = $event" @plan-generated="receivePlan" />
    <TripWorkspace ref="workspace" :draft="draft" :attractions="attractions" />
    <ElDialog v-model="replaceOpen" title="替换当前草案？" width="min(440px, 92vw)"
      :close-on-click-modal="false" @close="keepDraft">
      <p>当前草案尚未保存。替换后会丢失当前安排和修改，是否使用新生成的草案？</p>
      <template #footer>
        <ElButton @click="keepDraft">保留当前草案</ElButton>
        <ElButton type="primary" @click="replaceDraft">替换草案</ElButton>
      </template>
    </ElDialog>
  </main>
</template>
