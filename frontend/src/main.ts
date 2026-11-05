/**
 * 前端入口。挂载顺序：样式令牌 → pinia → router → Element Plus。
 *
 * 样式顺序不能反：tokens.scss 覆盖 Element Plus 的 --el-* 变量（01 §8），
 * 必须排在 element-plus 的样式之后才生效。
 * pinia 必须早于 router：路由守卫会调用 store，装晚了守卫里拿不到实例。
 */

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/tokens.scss'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
