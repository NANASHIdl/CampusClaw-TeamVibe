<script setup lang="ts">
/**
 * 资料详情页：元信息 + 切片列表（按 chunk_index 升序，MT-12）。
 *
 * `processing` 时明确显示「处理中，暂不可检索」，而不是给一个空切片列表让人以为没入库
 * （RT-09 的前端形态）。
 */

import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { downloadMaterialFile, getMaterial, type MaterialDetail } from '@/api/materials'
import { copy } from '@/constants/copy'
import { formatDateTime } from '@/utils/datetime'

type ViewState = 'loading' | 'ready' | 'error'

const route = useRoute()
const router = useRouter()

const state = ref<ViewState>('loading')
const detail = ref<MaterialDetail | null>(null)
const errorMessage = ref('')
const downloading = ref(false)

const materialId = computed(() => String(route.params.id ?? ''))
const searchable = computed(() => detail.value?.status === 'ready')

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function load(): Promise<void> {
  state.value = 'loading'
  errorMessage.value = ''
  try {
    detail.value = await getMaterial(materialId.value)
    state.value = 'ready'
  } catch (error) {
    errorMessage.value = (error as ApiError).message || copy.viewState.errorTitle
    state.value = 'error'
  }
}

function backToList(): void {
  void router.push({ name: 'materials' })
}

async function handleDownload(): Promise<void> {
  const item = detail.value
  if (!item) return
  downloading.value = true
  try {
    await downloadMaterialFile(item.id, item.original_filename)
  } catch (error) {
    ElMessage.error((error as ApiError).message || copy.error.unknown)
  } finally {
    downloading.value = false
  }
}

watch(materialId, load)
onMounted(load)
</script>

<template>
  <main class="cc-page">
    <div v-if="state === 'loading'" class="cc-card cc-state-card">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="state === 'error'" class="cc-card cc-state-card">
      <el-empty :description="errorMessage">
        <el-button type="primary" @click="load">{{ copy.viewState.errorRetry }}</el-button>
        <el-button @click="backToList">{{ copy.materials.backToList }}</el-button>
      </el-empty>
    </div>

    <template v-else-if="detail">
      <button type="button" class="cc-back" @click="backToList">
        ← {{ copy.materials.backToList }}
      </button>

      <section class="cc-card cc-detail-head">
        <div class="cc-detail-head__main">
          <h1 class="cc-page__title">{{ detail.title }}</h1>
          <div class="cc-meta">
            <span class="cc-mono">{{ detail.original_filename }}</span>
            <span>{{ formatSize(detail.size_bytes) }}</span>
            <span>{{ formatDateTime(detail.created_at) }}</span>
            <el-tag size="small">{{ copy.materials.status[detail.status] }}</el-tag>
            <span v-if="detail.status === 'ready'">
              {{ copy.materials.chunkCount.replace('{count}', String(detail.chunk_count)) }}
            </span>
          </div>
        </div>

        <el-button class="cc-detail-head__action" :loading="downloading" @click="handleDownload">
          {{ copy.materials.download }}
        </el-button>
      </section>

      <el-alert
        v-if="detail.status !== 'ready'"
        class="cc-detail__alert"
        type="warning"
        :closable="false"
        :title="
          detail.status === 'failed'
            ? `${copy.materials.failedReason}：${detail.failure_reason ?? ''}`
            : copy.materials.processingHint
        "
        show-icon
      />

      <template v-if="searchable">
        <h2 class="cc-section__title">{{ copy.materials.detailChunks }}</h2>
        <ol class="cc-chunks">
          <li v-for="chunk in detail.chunks" :key="chunk.chunk_index" class="cc-chunk">
            <div class="cc-chunk__head">
              <span class="cc-chunk__index">#{{ chunk.chunk_index }}</span>
              <span class="cc-hint">
                {{
                  copy.materials.chunkRange
                    .replace('{start}', String(chunk.char_start))
                    .replace('{end}', String(chunk.char_end))
                }}
              </span>
            </div>
            <p class="cc-chunk__body">{{ chunk.content }}</p>
          </li>
        </ol>
      </template>
    </template>
  </main>
</template>
