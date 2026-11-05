/**
 * 资料接口。
 *
 * 元数据走统一信封；原文下载是字节流（MT-14 约定了 Content-Type / Content-Disposition），
 * 单独用 `downloadMaterialFile` 抓 blob，理由见该函数的注释。
 */

import { copy } from '@/constants/copy'

import { ApiError, http, request, type Envelope } from './client'

export type MaterialStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface Material {
  id: string
  title: string
  original_filename: string
  mime: string
  size_bytes: number
  status: MaterialStatus
  failure_reason: string | null
  chunk_count: number
  created_at: string
}

export interface Chunk {
  chunk_index: number
  content: string
  char_count: number
  char_start: number
  char_end: number
}

export interface MaterialDetail extends Material {
  chunks: Chunk[]
}

export interface MaterialPage {
  total: number
  page: number
  page_size: number
  items: Material[]
}

export interface ListParams {
  page?: number
  page_size?: number
  sort?: 'created_at' | 'title'
  order?: 'asc' | 'desc'
  status?: MaterialStatus
}

export async function listMaterials(params: ListParams = {}): Promise<MaterialPage> {
  return request<MaterialPage>({ url: '/materials', method: 'get', params })
}

export async function getMaterial(id: string, chunkPage = 1): Promise<MaterialDetail> {
  return request<MaterialDetail>({
    url: `/materials/${id}`,
    method: 'get',
    params: { chunk_page: chunkPage },
  })
}

export async function uploadMaterials(
  files: File[],
): Promise<{ total: number; items: Material[] }> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  // 不手写 Content-Type：交给浏览器带 boundary，手写会导致后端解析失败
  return request<{ total: number; items: Material[] }>({
    url: '/materials',
    method: 'post',
    data: form,
  })
}

export async function deleteMaterial(id: string): Promise<{ id: string; deleted_at: string }> {
  return request<{ id: string; deleted_at: string }>({
    url: `/materials/${id}`,
    method: 'delete',
  })
}

/** 原文下载地址。只用于「复制链接」等场景；页面上的下载按钮走 `downloadMaterialFile`。 */
export function materialFileUrl(id: string): string {
  return `/api/v1/materials/${id}/file`
}

/**
 * 下载原文。
 *
 * 为什么不是 `<a href>`：会话过期时那个地址回的是 401 + JSON 信封，浏览器会把
 * 一屏 `{"code":1101,...}` 直接铺在新标签页上，用户只看到「点了没反应/乱码」。
 * 这里改成抓 blob 再触发保存，失败才能翻译成一句「登录已过期，请重新登录」。
 *
 * 后端 4xx 的响应体也是 JSON（bytes 流里没有信封），所以先按 Blob 收，再解一次。
 */
export async function downloadMaterialFile(id: string, filename: string): Promise<void> {
  const response = await http.get<Blob>(`/materials/${id}/file`, {
    responseType: 'blob',
    validateStatus: () => true,
    timeout: 60000,
  })

  if (response.status !== 200) {
    let code = -1
    let message: string = copy.error.unknown
    let requestId = ''
    try {
      const envelope = JSON.parse(await (response.data as Blob).text()) as Envelope<null>
      code = envelope.code
      message = envelope.message
      requestId = envelope.request_id
    } catch {
      message = response.status === 401 ? copy.error.unauthorized : copy.error.unknown
    }
    throw new ApiError(code, message, requestId)
  }

  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
