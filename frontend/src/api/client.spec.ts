/**
 * 请求标识生成器的用例。
 *
 * 覆盖的 Scenario：
 * - PC-08 请求标识格式为 26 位大写 ULID，可与后端 core/ids.py 的校验器互通
 */

import { describe, expect, it } from 'vitest'

import { newUlid } from './client'

const ULID_PATTERN = /^[0-9A-HJKMNP-TV-Z]{26}$/

describe('newUlid', () => {
  it('生成 26 位大写 Crockford Base32', () => {
    const id = newUlid()

    expect(id).toHaveLength(26)
    expect(id).toMatch(ULID_PATTERN)
  })

  it('同一毫秒内连续生成不重复', () => {
    const ids = new Set(Array.from({ length: 500 }, () => newUlid()))

    expect(ids.size).toBe(500)
  })

  it('前 10 位是当前毫秒时间戳（ULID 的时间有序性来源）', () => {
    const alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    const id = newUlid()

    let timestamp = 0
    for (const char of id.slice(0, 10)) {
      timestamp = timestamp * 32 + alphabet.indexOf(char)
    }

    // 允许 5 秒误差：只验证「时间戳在高位且是当前时间」，不验证毫秒精确值
    expect(Math.abs(timestamp - Date.now())).toBeLessThan(5000)
  })

  it('跨毫秒生成时字典序递增（同一毫秒内不保证，随机后缀会打乱）', async () => {
    const first = newUlid()
    await new Promise((resolve) => setTimeout(resolve, 5))
    const later = newUlid()

    expect(later > first).toBe(true)
  })
})
