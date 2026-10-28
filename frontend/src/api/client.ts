/**
 * axios 实例与统一错误映射。
 *
 * 规范依据：
 * - openspec/changes/2026-10-28-bootstrap-skeleton/design.md §6
 *   「api/ 层统一把 {code,message,data} 拆开：code !== 0 抛 ApiError，视图只处理成功分支与错误块」
 * - docs/specs/02-后端开发规范.md §3（统一信封）
 *
 * 页面**不得**直接读 response.data.data；一律 await request<T>() 拿 data。
 */

import axios, { AxiosError, type AxiosRequestConfig } from 'axios'

import { copy } from '@/constants/copy'

export interface Envelope<T> {
  code: number
  message: string
  data: T
  request_id: string
}

export class ApiError extends Error {
  readonly code: number
  readonly requestId: string

  constructor(code: number, message: string, requestId = '') {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.requestId = requestId
  }
}

const ULID_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

/** 生成 26 位 ULID，用于 X-Request-ID（与后端 core/ids.py 同一字母表、同一字节序）。 */
export function newUlid(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)

  // 前 10 位：48 位毫秒时间戳，**大端**（高位在前），否则字典序不随时间递增，
  // 与后端 core/ids.py 的解码也对不上。
  const timeChars: string[] = []
  let ts = Date.now()
  for (let i = 0; i < 10; i += 1) {
    timeChars.push(ULID_ALPHABET[ts % 32])
    ts = Math.floor(ts / 32)
  }

  // 后 16 位：80 位随机数
  const randomChars: string[] = []
  for (let i = 0; i < 16; i += 1) {
    randomChars.push(ULID_ALPHABET[bytes[i] % 32])
  }

  return timeChars.reverse().join('') + randomChars.join('')
}

const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  withCredentials: true,
})

http.interceptors.request.use((config) => {
  config.headers.set('X-Request-ID', newUlid())
  return config
})

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  const axiosError = error as AxiosError<Envelope<null>>
  const body = axiosError.response?.data
  if (body && typeof body.code === 'number') {
    return new ApiError(body.code, body.message, body.request_id)
  }
  if (axiosError.response?.status === 401) {
    return new ApiError(1101, copy.error.unauthorized)
  }
  if (axiosError.response?.status === 404) {
    return new ApiError(1301, copy.error.notFound)
  }
  return new ApiError(-1, copy.error.network)
}

/** 发一个业务请求并返回 data；code !== 0 一律抛 ApiError。 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await http.request<Envelope<T>>(config)
    const envelope = response.data
    if (envelope.code !== 0) {
      throw new ApiError(envelope.code, envelope.message, envelope.request_id)
    }
    return envelope.data
  } catch (error) {
    throw toApiError(error)
  }
}

export { http }
