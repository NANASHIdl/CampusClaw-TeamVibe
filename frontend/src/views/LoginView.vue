<script setup lang="ts">
/**
 * 登录页。四状态齐全（01 §7）：默认、提交中、失败、锁定。
 *
 * 表单校验时机：失焦与提交时校验，不等输入过程就报红（01 §6）。
 * 这里不存任何令牌——登录成功由服务端下发 HttpOnly Cookie。
 *
 * 默认账号区只在开发/演示构建出现：`import.meta.env.DEV` 或显式打开
 * `VITE_SHOW_DEMO_ACCOUNTS`（compose 的本机演示构建打开）。
 * 口令来自构建期注入的 `VITE_DEMO_*_PASSWORD`；没有注入时只填邮箱，
 * 提示去 .env 取——正式部署不会把口令打进产物（AGENTS.md §1.3）。
 */

import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { InputInstance } from 'element-plus'

import { ApiError } from '@/api/client'
import { copy } from '@/constants/copy'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const passwordInput = ref<InputInstance>()

const showDemoAccounts = import.meta.env.DEV || import.meta.env.VITE_SHOW_DEMO_ACCOUNTS === 'true'

/** 构建期注入的测试口令；为空说明这个构建不该显示口令 */
const DEMO_PASSWORDS: Record<string, string> = {
  teacher: import.meta.env.VITE_DEMO_TEACHER_PASSWORD ?? '',
  student: import.meta.env.VITE_DEMO_STUDENT_PASSWORD ?? '',
}

const hasDemoPasswords = Object.values(DEMO_PASSWORDS).some((item) => item !== '')

const EMAIL_RE = /^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/

function validate(): boolean {
  if (!EMAIL_RE.test(email.value)) {
    errorMessage.value = copy.auth.emailInvalid
    return false
  }
  if (password.value.length < 8 || password.value.length > 72) {
    errorMessage.value = copy.auth.passwordInvalid
    return false
  }
  return true
}

function fillDemoAccount(accountEmail: string, key: string): void {
  email.value = accountEmail
  const demoPassword = DEMO_PASSWORDS[key] ?? ''
  if (demoPassword) {
    password.value = demoPassword
    errorMessage.value = ''
    return
  }
  errorMessage.value = ''
  passwordInput.value?.focus()
}

async function submit(): Promise<void> {
  errorMessage.value = ''
  if (!validate()) return

  submitting.value = true
  try {
    await auth.signIn(email.value, password.value)
    const next = typeof route.query.next === 'string' ? route.query.next : '/materials'
    await router.replace(next)
  } catch (error) {
    const apiError = error as ApiError
    errorMessage.value =
      apiError.code === 1601 ? copy.auth.locked : apiError.message || copy.auth.failed
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="cc-login">
    <div class="cc-login__panel">
      <section class="cc-login__hero">
        <span class="cc-login__hero-badge">{{ copy.auth.heroBadge }}</span>
        <h1 class="cc-login__hero-title">{{ copy.auth.heroTitle }}</h1>
        <p class="cc-login__hero-text">{{ copy.auth.heroText }}</p>

        <ul class="cc-login__points">
          <li
            v-for="(point, index) in copy.auth.heroPoints"
            :key="point.title"
            class="cc-login__point"
          >
            <span class="cc-login__point-index" aria-hidden="true">{{ index + 1 }}</span>
            <div>
              <p class="cc-login__point-title">{{ point.title }}</p>
              <p class="cc-login__point-text">{{ point.text }}</p>
            </div>
          </li>
        </ul>
      </section>

      <section class="cc-login__form-side">
        <h2 class="cc-login__title">{{ copy.auth.welcomeTitle }}</h2>
        <p class="cc-login__subtitle">{{ copy.auth.welcomeText }}</p>

        <el-alert
          v-if="errorMessage"
          class="cc-login__alert"
          type="error"
          :title="errorMessage"
          :closable="false"
          show-icon
        />

        <form class="cc-login__form" @submit.prevent="submit">
          <label class="cc-login__label" for="email">{{ copy.auth.email }}</label>
          <el-input
            id="email"
            v-model="email"
            :placeholder="copy.auth.emailPlaceholder"
            autocomplete="username"
            size="large"
          />

          <label class="cc-login__label" for="password">{{ copy.auth.password }}</label>
          <el-input
            id="password"
            ref="passwordInput"
            v-model="password"
            type="password"
            :placeholder="copy.auth.passwordPlaceholder"
            autocomplete="current-password"
            size="large"
            show-password
          />

          <el-button
            class="cc-login__submit"
            type="primary"
            size="large"
            native-type="submit"
            :loading="submitting"
          >
            {{ submitting ? copy.auth.submitting : copy.auth.submit }}
          </el-button>
        </form>

        <div v-if="showDemoAccounts" class="cc-demo">
          <p class="cc-demo__title">{{ copy.auth.demo.title }}</p>
          <p class="cc-demo__hint">
            {{ hasDemoPasswords ? copy.auth.demo.hint : copy.auth.demo.hintNoPassword }}
          </p>
          <div class="cc-demo__list">
            <button
              v-for="account in copy.auth.demo.accounts"
              :key="account.email"
              type="button"
              class="cc-demo__account"
              @click="fillDemoAccount(account.email, account.key)"
            >
              <span class="cc-demo__role">{{ account.role }}</span>
              <span class="cc-demo__cred">
                <span class="cc-demo__mail">{{ account.email }}</span>
                <span v-if="hasDemoPasswords" class="cc-demo__pass">{{
                  DEMO_PASSWORDS[account.key]
                }}</span>
              </span>
              <span class="cc-demo__action">{{ copy.auth.demo.fill }}</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
