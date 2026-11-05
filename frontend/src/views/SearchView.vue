<script setup lang="ts">
/**
 * 检索页。三模式可切换，结果带出处（材料标题 + 切片序号 + 字符区间）。
 *
 * 无命中时显示固定文案与两个动作，而不是空白列表（RT-08 的前端形态）。
 * `class_id` 不在这里出现——班级由服务端会话决定。
 */

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { search, type SearchMode, type SearchResult } from '@/api/search'
import { copy } from '@/constants/copy'

type ViewState = 'idle' | 'loading' | 'ready' | 'empty' | 'error'

const router = useRouter()

const query = ref('')
const mode = ref<SearchMode>('hybrid')
const state = ref<ViewState>('idle')
const result = ref<SearchResult | null>(null)
const errorMessage = ref('')

const MODE_OPTIONS: { value: SearchMode; label: string }[] = [
  { value: 'hybrid', label: copy.search.modes.hybrid },
  { value: 'keyword', label: copy.search.modes.keyword },
  { value: 'vector', label: copy.search.modes.vector },
]

const modeHint = computed(() => copy.search.modeHint[mode.value])

function scoreText(score: number): string {
  return copy.search.score.replace('{score}', score.toFixed(2))
}

function useExample(example: string): void {
  query.value = example
  void submit()
}

async function submit(): Promise<void> {
  errorMessage.value = ''
  if (query.value.trim().length < 2) {
    errorMessage.value = copy.search.tooShort
    state.value = 'error'
    return
  }

  state.value = 'loading'
  try {
    const payload = await search(query.value.trim(), mode.value)
    result.value = payload
    state.value = payload.hits.length > 0 ? 'ready' : 'empty'
  } catch (error) {
    errorMessage.value = (error as ApiError).message || copy.viewState.errorTitle
    state.value = 'error'
  }
}

function retryWithNewKeyword(): void {
  state.value = 'idle'
  query.value = ''
}

function goToMaterials(): void {
  void router.push({ name: 'materials' })
}
</script>

<template>
  <main class="cc-page">
    <div class="cc-page__head">
      <div>
        <h1 class="cc-page__title">{{ copy.search.title }}</h1>
        <p class="cc-page__description">{{ copy.search.description }}</p>
      </div>
    </div>

    <section class="cc-card cc-search-panel">
      <form class="cc-search" @submit.prevent="submit">
        <el-input
          v-model="query"
          class="cc-search__input"
          :placeholder="copy.search.placeholder"
          size="large"
          maxlength="200"
        />
        <el-select v-model="mode" class="cc-search__mode" size="large">
          <el-option
            v-for="option in MODE_OPTIONS"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button type="primary" size="large" native-type="submit" :loading="state === 'loading'">
          {{ state === 'loading' ? copy.search.searching : copy.search.submit }}
        </el-button>
      </form>

      <p class="cc-hint cc-search__mode-hint">{{ modeHint }}</p>

      <div class="cc-search__examples">
        <span class="cc-hint">{{ copy.search.examplesLabel }}</span>
        <button
          v-for="example in copy.search.examples"
          :key="example"
          type="button"
          class="cc-chip"
          @click="useExample(example)"
        >
          {{ example }}
        </button>
      </div>
    </section>

    <div v-if="state === 'loading'" class="cc-card cc-state-card">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="state === 'error'" class="cc-card cc-state-card">
      <el-empty :description="errorMessage" />
    </div>

    <div v-else-if="state === 'empty'" class="cc-card cc-state-card">
      <el-empty :description="copy.retrieval.noHit">
        <el-button type="primary" @click="retryWithNewKeyword">
          {{ copy.retrieval.noHitActionSearch }}
        </el-button>
        <el-button @click="goToMaterials">{{ copy.retrieval.noHitActionUpload }}</el-button>
      </el-empty>
    </div>

    <div v-else-if="state === 'idle'" class="cc-card cc-state-card">
      <div class="cc-empty-hint">
        <p class="cc-empty-hint__title">{{ copy.search.idleTitle }}</p>
        <p class="cc-hint">{{ copy.search.idleText }}</p>
      </div>
    </div>

    <template v-else-if="state === 'ready' && result">
      <p class="cc-hint cc-result-count">
        {{ copy.search.resultCount.replace('{count}', String(result.total)) }}
      </p>
      <ul class="cc-hits">
        <li
          v-for="hit in result.hits"
          :key="`${hit.material_id}-${hit.chunk_index}`"
          class="cc-hit"
        >
          <div class="cc-hit__head">
            <span class="cc-hit__title">{{ hit.title }}</span>
            <span class="cc-hit__score">{{ scoreText(hit.score) }}</span>
          </div>
          <p class="cc-hit__snippet">{{ hit.snippet }}</p>
          <div class="cc-hit__meta">
            <span class="cc-hint">
              {{ copy.search.hitLocation.replace('{index}', String(hit.chunk_index)) }}
            </span>
            <RouterLink
              class="cc-link"
              :to="{ name: 'material-detail', params: { id: hit.material_id } }"
            >
              {{ copy.materials.openDetail }}
            </RouterLink>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
