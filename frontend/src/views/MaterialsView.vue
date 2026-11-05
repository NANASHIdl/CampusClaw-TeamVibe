<script setup lang="ts">
/**
 * 资料列表页。四状态齐全：加载中 / 正常 / 错误 / 空状态。
 *
 * 上传入口只对教师显示，但**权限不靠隐藏按钮**——服务端对同班学生会返回 404 1202
 * （AGENTS.md §1.1），隐藏只是少给一次无效点击。
 */

import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import {
  deleteMaterial,
  downloadMaterialFile,
  listMaterials,
  uploadMaterials,
  type Material,
} from '@/api/materials'
import { copy } from '@/constants/copy'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/datetime'

type ViewState = 'loading' | 'ready' | 'error' | 'empty'

const auth = useAuthStore()
const router = useRouter()

const state = ref<ViewState>('loading')
const items = ref<Material[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const errorMessage = ref('')
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const isTeacher = computed(() => auth.user?.role === 'teacher')

const STATUS_TAG: Record<Material['status'], 'info' | 'warning' | 'success' | 'danger'> = {
  pending: 'info',
  processing: 'warning',
  ready: 'success',
  failed: 'danger',
}

function statusLabel(status: Material['status']): string {
  return copy.materials.status[status]
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function load(): Promise<void> {
  state.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await listMaterials({ page: page.value, page_size: pageSize.value })
    items.value = result.items
    total.value = result.total
    state.value = result.items.length > 0 ? 'ready' : 'empty'
  } catch (error) {
    errorMessage.value = (error as ApiError).message || copy.viewState.errorTitle
    state.value = 'error'
  }
}

async function changePage(next: number): Promise<void> {
  page.value = next
  await load()
}

function pickFiles(): void {
  fileInput.value?.click()
}

async function handleFiles(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const chosen = Array.from(target.files ?? [])
  target.value = ''
  if (chosen.length === 0) return

  uploading.value = true
  try {
    await uploadMaterials(chosen)
    ElMessage.success(copy.materials.uploadDone)
    page.value = 1
    await load()
  } catch (error) {
    ElMessage.error(`${copy.materials.uploadRejected}：${(error as ApiError).message}`)
  } finally {
    uploading.value = false
  }
}

async function remove(material: Material): Promise<void> {
  try {
    await ElMessageBox.confirm(copy.materials.deleteConfirm, copy.materials.delete, {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteMaterial(material.id)
    await load()
  } catch (error) {
    ElMessage.error((error as ApiError).message)
  }
}

function openDetail(material: Material): void {
  void router.push({ name: 'material-detail', params: { id: material.id } })
}

async function download(material: Material): Promise<void> {
  try {
    await downloadMaterialFile(material.id, material.original_filename)
  } catch (error) {
    ElMessage.error((error as ApiError).message || copy.error.unknown)
  }
}

onMounted(load)
</script>

<template>
  <main class="cc-page">
    <div class="cc-page__head">
      <div>
        <h1 class="cc-page__title">{{ copy.materials.title }}</h1>
        <p class="cc-page__description">{{ copy.materials.description }}</p>
      </div>

      <div v-if="isTeacher" class="cc-toolbar">
        <el-button type="primary" :loading="uploading" @click="pickFiles">
          {{ uploading ? copy.materials.uploading : copy.materials.upload }}
        </el-button>
        <input
          ref="fileInput"
          class="cc-hidden"
          type="file"
          accept=".md,.txt"
          multiple
          @change="handleFiles"
        />
      </div>
    </div>

    <p v-if="isTeacher" class="cc-hint cc-upload-hint">{{ copy.materials.uploadHint }}</p>

    <div v-if="state !== 'ready'" class="cc-card cc-state-card">
      <el-skeleton v-if="state === 'loading'" :rows="5" animated />

      <el-empty v-else-if="state === 'error'" :description="errorMessage">
        <el-button type="primary" @click="load">{{ copy.viewState.errorRetry }}</el-button>
      </el-empty>

      <el-empty
        v-else-if="state === 'empty'"
        :description="isTeacher ? copy.materials.emptyForTeacher : copy.materials.emptyForStudent"
      />
    </div>

    <template v-if="state === 'ready'">
      <div class="cc-card cc-table-card">
        <el-table :data="items" class="cc-table" @row-click="openDetail">
          <el-table-column :label="copy.materials.columnTitle" min-width="260">
            <template #default="{ row }">
              <div class="cc-material__title">{{ row.title }}</div>
              <div class="cc-material__file">{{ row.original_filename }}</div>
            </template>
          </el-table-column>
          <el-table-column :label="copy.materials.columnSize" width="110">
            <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
          </el-table-column>
          <el-table-column prop="chunk_count" :label="copy.materials.columnChunks" width="90" />
          <el-table-column :label="copy.materials.columnStatus" width="120">
            <template #default="{ row }">
              <el-tag :type="STATUS_TAG[row.status as Material['status']]" size="small">
                {{ statusLabel(row.status as Material['status']) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="copy.materials.columnCreatedAt" width="180">
            <template #default="{ row }">
              <span class="cc-date">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="copy.materials.columnActions" width="150" align="right">
            <template #default="{ row }">
              <el-button link type="primary" @click.stop="download(row as Material)">
                {{ copy.materials.download }}
              </el-button>
              <el-button v-if="isTeacher" link type="danger" @click.stop="remove(row as Material)">
                {{ copy.materials.delete }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="cc-pager">
          <span class="cc-hint">
            {{
              copy.materials.pageInfo
                .replace('{page}', String(page))
                .replace('{pages}', String(Math.max(Math.ceil(total / pageSize), 1)))
                .replace('{total}', String(total))
            }}
          </span>
          <div class="cc-pager__actions">
            <el-button :disabled="page <= 1" @click="changePage(page - 1)">
              {{ copy.materials.pagePrev }}
            </el-button>
            <el-button :disabled="page * pageSize >= total" @click="changePage(page + 1)">
              {{ copy.materials.pageNext }}
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </main>
</template>
