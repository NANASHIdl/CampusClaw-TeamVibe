/**
 * 路由表与守卫。
 *
 * 产品规范 §2 的页面清单是唯一出处。守卫只做「未登录去登录页」这一件事——
 * 权限判定在服务端，前端隐藏入口不是授权手段（03 §2）。
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/materials',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/materials',
    name: 'materials',
    component: () => import('@/views/MaterialsView.vue'),
  },
  {
    path: '/materials/:id',
    name: 'material-detail',
    component: () => import('@/views/MaterialDetailView.vue'),
  },
  {
    path: '/search',
    name: 'search',
    component: () => import('@/views/SearchView.vue'),
  },
  {
    path: '/health',
    name: 'health',
    component: () => import('@/views/HealthView.vue'),
    meta: { public: true },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.load()

  if (to.meta.public) {
    // 已登录还去登录页，直接送回列表
    if (to.name === 'login' && auth.user) {
      return { name: 'materials' }
    }
    return true
  }

  if (!auth.user) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  return true
})

export default router
