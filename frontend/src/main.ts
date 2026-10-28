/**
 * 前端入口。挂载顺序：样式令牌 → router → pinia → Element Plus。
 *
 * 样式顺序不能反：tokens.scss 覆盖 Element Plus 的 --el-* 变量（01 §8），
 * 必须排在 element-plus 的样式之后才生效。
 */

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/tokens.scss'

const app = createApp(App)

app.use(router)
app.use(createPinia())
app.use(ElementPlus)

app.mount('#app')
