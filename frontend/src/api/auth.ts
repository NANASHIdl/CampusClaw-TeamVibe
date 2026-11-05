/**
 * 身份接口。
 *
 * 令牌不下发到前端：登录成功后浏览器自动持有 HttpOnly Cookie，后续请求靠
 * `withCredentials` 带上（client.ts 已配好）。所以这里的类型里没有 token 字段，
 * 也不应该有。
 */

import { request } from './client'

export interface ClassBrief {
  id: string
  name: string
  role: 'teacher' | 'student'
}

export interface SessionUser {
  id: string
  display_name: string
  role: 'teacher' | 'student'
  class_id: string | null
  classes: ClassBrief[]
}

export async function login(email: string, password: string): Promise<SessionUser> {
  return request<SessionUser>({
    url: '/auth/login',
    method: 'post',
    data: { email, password },
  })
}

export async function logout(): Promise<void> {
  await request<{ logged_out: boolean }>({ url: '/auth/logout', method: 'post' })
}

export async function fetchMe(): Promise<SessionUser> {
  return request<SessionUser>({ url: '/me', method: 'get' })
}
