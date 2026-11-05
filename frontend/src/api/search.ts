/**
 * 检索接口。
 *
 * `class_id` 不在参数里，也不该在前端出现——班级由服务端会话决定（AGENTS.md §1.2）。
 * 传了也会被忽略，但更该做的是根本不传。
 */

import { request } from './client'

export type SearchMode = 'keyword' | 'vector' | 'hybrid'

export interface SearchHit {
  material_id: string
  chunk_index: number
  title: string
  snippet: string
  score: number
  char_start: number
  char_end: number
}

export interface SearchResult {
  mode: SearchMode
  hits: SearchHit[]
  total: number
  message: string | null
}

export async function search(q: string, mode: SearchMode = 'hybrid'): Promise<SearchResult> {
  return request<SearchResult>({ url: '/search', method: 'get', params: { q, mode } })
}
