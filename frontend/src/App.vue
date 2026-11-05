<script setup lang="ts">
/**
 * 应用外壳：登录后才有导航（第 1 课：产品入口是登录，不是打开即输入框）。
 *
 * 顶栏只展示「我是谁、我在哪个班」这类会话信息，全部来自 /me，
 * 不接受任何 URL 或 localStorage 里的角色声明。
 */

import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import { copy } from '@/constants/copy'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const signedIn = computed(() => Boolean(auth.user))
const activeClass = computed(
  () => auth.user?.classes.find((item) => item.id === auth.user?.class_id) ?? null,
)
const initial = computed(() => auth.user?.display_name.trim().charAt(0) ?? '')
const roleLabel = computed(() =>
  auth.user?.role === 'teacher' ? copy.roles.teacher : copy.roles.student,
)

async function handleSignOut(): Promise<void> {
  await auth.signOut()
  await router.push({ name: 'login' })
}
</script>

<template>
  <header v-if="signedIn" class="cc-header">
    <div class="cc-header__inner">
      <RouterLink class="cc-header__brand" to="/materials">
        <span class="cc-header__logo" aria-hidden="true">{{ copy.brandMark }}</span>
        <span class="cc-header__wordmark">
          <span class="cc-header__name">{{ copy.brandName }}</span>
          <span class="cc-header__team">{{ copy.brandTeam }}</span>
        </span>
      </RouterLink>

      <span v-if="activeClass" class="cc-header__class">{{ activeClass.name }}</span>

      <nav class="cc-header__nav" :aria-label="copy.nav.label">
        <RouterLink to="/materials">{{ copy.nav.materials }}</RouterLink>
        <RouterLink to="/search">{{ copy.nav.search }}</RouterLink>
        <RouterLink to="/health">{{ copy.nav.health }}</RouterLink>
      </nav>

      <div class="cc-header__user">
        <span class="cc-header__avatar" aria-hidden="true">{{ initial }}</span>
        <span class="cc-header__who">
          <span class="cc-header__who-name">{{ auth.user?.display_name }}</span>
          <span class="cc-header__who-role">{{ roleLabel }}</span>
        </span>
        <el-button link type="primary" @click="handleSignOut">{{ copy.nav.logout }}</el-button>
      </div>
    </div>
  </header>
  <RouterView />
</template>
