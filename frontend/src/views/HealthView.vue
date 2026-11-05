<script setup lang="ts">
/**
 * 探活页。骨架期唯一页面，用于验证「clone → 填 .env → 一条命令启动 → 看得到依赖状态」。
 *
 * 视图四状态齐全（01 §7）：加载中 / 正常 / 错误 / 空状态。
 * 只用 01 §8 组件清单里的组件，不写内联 style。
 */

import { onMounted, ref } from 'vue'

import { getHealth, type HealthPayload } from '@/api/health'
import { copy } from '@/constants/copy'
import { formatDateTime } from '@/utils/datetime'

type ViewState = 'loading' | 'ready' | 'error' | 'empty'

const state = ref<ViewState>('loading')
const payload = ref<HealthPayload | null>(null)
const errorMessage = ref('')

async function load(): Promise<void> {
  state.value = 'loading'
  errorMessage.value = ''
  try {
    payload.value = await getHealth()
    const deps = payload.value.deps ?? {}
    state.value = Object.keys(deps).length > 0 ? 'ready' : 'empty'
  } catch {
    errorMessage.value = copy.error.network
    state.value = 'error'
  }
}

function depLabel(key: string): string {
  const labels = copy.health.depLabels as Record<string, string>
  return labels[key] ?? key
}

onMounted(load)
</script>

<template>
  <main class="cc-page">
    <div class="cc-page__head">
      <div>
        <h1 class="cc-page__title">{{ copy.health.title }}</h1>
        <p class="cc-page__description">{{ copy.health.description }}</p>
      </div>
      <el-button @click="load">{{ copy.health.retry }}</el-button>
    </div>

    <div v-if="state === 'loading'" class="cc-card cc-state-card">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="state === 'error'" class="cc-card cc-state-card">
      <el-empty :description="errorMessage">
        <el-button type="primary" @click="load">{{ copy.viewState.errorRetry }}</el-button>
      </el-empty>
    </div>

    <div v-else-if="state === 'empty'" class="cc-card cc-state-card">
      <el-empty :description="copy.viewState.emptyDescription" />
    </div>

    <section v-else-if="payload" class="cc-card cc-card--padded">
      <div class="cc-health__header">
        <el-tag :type="payload.status === 'ok' ? 'success' : 'warning'" size="large">
          {{ payload.status === 'ok' ? copy.health.statusOk : copy.health.statusDegraded }}
        </el-tag>
      </div>

      <div class="cc-health__deps">
        <div v-for="(value, key) in payload.deps" :key="key" class="cc-health__dep">
          <span>{{ depLabel(String(key)) }}</span>
          <el-tag :type="value === 'up' ? 'success' : 'danger'" size="small">
            {{ value === 'up' ? copy.health.depUp : copy.health.depDown }}
          </el-tag>
        </div>
      </div>

      <div class="cc-health__meta">
        <span>{{ copy.health.version }}：{{ payload.version }}</span>
        <span>{{ copy.health.commit }}：{{ payload.commit }}</span>
        <span>{{ copy.health.time }}：{{ formatDateTime(payload.time) }}</span>
      </div>
    </section>
  </main>
</template>
