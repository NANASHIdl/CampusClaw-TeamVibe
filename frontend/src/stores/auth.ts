/**
 * 登录态 store。
 *
 * 只缓存「我是谁、我是哪个班的」这类展示信息，不缓存令牌——令牌在 HttpOnly Cookie 里，
 * 前端读不到也不该读（03 §5）。刷新页面时靠 `/me` 重新确认，而不是靠 localStorage。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchMe, login as loginApi, logout as logoutApi, type SessionUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<SessionUser | null>(null)
  const loaded = ref(false)

  async function load(): Promise<void> {
    if (loaded.value) return
    try {
      user.value = await fetchMe()
    } catch {
      // 未登录就是未登录，不区分「没 Cookie」和「会话过期」——对页面而言结果一样
      user.value = null
    } finally {
      loaded.value = true
    }
  }

  async function signIn(email: string, password: string): Promise<void> {
    user.value = await loginApi(email, password)
    loaded.value = true
  }

  async function signOut(): Promise<void> {
    try {
      await logoutApi()
    } finally {
      user.value = null
      loaded.value = true
    }
  }

  return { user, loaded, load, signIn, signOut }
})
