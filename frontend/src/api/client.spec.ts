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

  it('字典序与时间顺序一致（时间戳在高位）', () => {
    const first = newUlid()
    const later = newUlid()

    expect(later >= first).toBe(true)
  })
})
