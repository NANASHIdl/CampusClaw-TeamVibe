/**
 * 健康检查接口。
 *
 * `/health` 是 02 §3 的唯一例外：**不走统一信封**，所以这里用裸 axios，
 * 不经过 client.ts 的 request<T>() 解包。
 */

import axios from 'axios'

export interface HealthPayload {
  status: 'ok' | 'degraded'
  version: string
  commit: string
  time: string
  deps?: Record<string, 'up' | 'down'>
}

const raw = axios.create({ timeout: 5000 })

/** 拿综合体检结果。503 也是有效响应（degraded），只有连不上才抛错。 */
export async function getHealth(): Promise<HealthPayload> {
  const response = await raw.get<HealthPayload>('/health', {
    validateStatus: (status) => status === 200 || status === 503,
  })
  return response.data
}
