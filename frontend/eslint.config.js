import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'playwright-report/**'],
  },
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    rules: {
      // 文案集中在 constants/copy.ts，模板里允许直接引用对象
      'vue/multi-word-component-names': 'off',
      // 排版交给 Prettier（.prettierrc.json）。这两条规则与 Prettier 的折行策略冲突，
      // 同时开启会出现「eslint --fix 改回去、prettier 又改回来」的来回拉扯。
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
    },
  },
)
