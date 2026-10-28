/**
 * 路由表。骨架期只有探活页。
 *
 * 后续能力的路由（/login、/materials、/console、/ask、/sessions）与路由守卫
 * 见 tasks.md 第 2 组起；产品规范 §2 的页面清单是唯一出处。
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/health',
  },
  {
    path: '/health',
    name: 'health',
    component: () => import('@/views/HealthView.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
