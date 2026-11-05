/**
 * 全部中文文案的唯一出处。
 *
 * 规范依据：docs/specs/01-产品设计规范.md §5（文案与术语表）
 * 页面里不写字符串字面量——改文案只改这里，避免同一个意思出现三种说法。
 */

export const copy = {
  appName: 'CampusClaw · TeamVibe',
  appTagline: '按班级隔离的课程知识库与解题助手',
  brandMark: 'CC',
  brandName: 'CampusClaw',
  brandTeam: 'TeamVibe',

  roles: {
    teacher: '教师',
    student: '学生',
  },

  /** 视图四状态：加载中 / 正常 / 错误 / 空状态 */
  viewState: {
    loading: '正在加载…',
    errorTitle: '加载失败',
    errorRetry: '重新加载',
    emptyTitle: '暂无数据',
    emptyDescription: '当前还没有可展示的内容',
  },

  nav: {
    label: '主导航',
    materials: '本班资料',
    search: '检索',
    health: '服务体检',
    logout: '退出登录',
  },

  auth: {
    title: '登录',
    description: '教师上传本班资料，学生检索本班资料提问；未登录看不到任何资料。',
    welcomeTitle: '登录后继续',
    welcomeText: '使用本班账号登录，未登录看不到任何资料。',
    heroBadge: '按班级隔离的课程知识库',
    heroTitle: '本班资料，本班可见。',
    heroText: '教师上传讲义，学生在本班范围内检索；每条结果都能回到原文的具体切片。',
    heroPoints: [
      {
        title: '班级即边界',
        text: '跨班访问与「资源不存在」返回完全一致的 404，看不出隔壁班有什么。',
      },
      {
        title: '出处可回溯',
        text: '命中附带资料标题、切片序号与字符区间，点开就能核对原文。',
      },
      {
        title: '没依据就直说',
        text: '检索不到时返回固定文案「资料中未找到相关内容」，不编造答案。',
      },
    ],
    email: '邮箱',
    emailPlaceholder: 'name@pku.edu.cn',
    password: '口令',
    passwordPlaceholder: '8–72 位',
    submit: '登录',
    submitting: '正在登录…',
    emailInvalid: '请填写有效的邮箱地址',
    passwordInvalid: '口令长度需在 8–72 位之间',
    /** 不区分「用户不存在」与「口令错误」，与后端文案一致 */
    failed: '邮箱或口令不正确',
    locked: '尝试过于频繁，请稍后再试',
    /**
     * 测试账号区。邮箱是固定种子，写在文案里无所谓；
     * **口令只有在构建时显式打开 `VITE_SHOW_DEMO_ACCOUNTS` 并且注入了
     * `VITE_DEMO_*_PASSWORD` 才会出现**——默认构建（含正式部署）只显示邮箱，
     * 避免口令随镜像扩散（AGENTS.md §1.3）。
     */
    demo: {
      title: '测试账号',
      hint: '点任意一行，邮箱与口令一并填入。',
      hintNoPassword:
        '点任意一行填入邮箱；口令见本机 .env 的 SEED_TEACHER_PASSWORD / SEED_STUDENT_PASSWORD。',
      fill: '一键填入',
      accounts: [
        { key: 'teacher', role: '教师 · 1 班', email: 'teacher@pku.edu.cn' },
        { key: 'student', role: '学生 · 1 班', email: 'student@pku.edu.cn' },
        { key: 'teacher', role: '教师 · 2 班', email: 'teacher+b@pku.edu.cn' },
        { key: 'student', role: '学生 · 2 班', email: 'student+b@pku.edu.cn' },
      ],
    },
  },

  health: {
    title: '服务体检',
    description: '免认证端点，用于确认后端与三项依赖是否可用。',
    statusOk: '正常',
    statusDegraded: '降级',
    depUp: '可用',
    depDown: '不可达',
    depLabels: {
      db: '数据库',
      qdrant: '向量库',
      llm: '模型服务',
    },
    version: '版本',
    commit: '提交',
    time: '检测时间',
    retry: '重新检测',
  },

  materials: {
    title: '本班资料',
    description: '只显示当前班级的资料；其他班的资料即使知道编号也打不开。',
    upload: '上传资料',
    uploading: '正在上传…',
    uploadHint: '支持 .md / .txt，单个不超过 20 MiB，单批不超过 20 个',
    empty: '本班还没有资料',
    emptyForTeacher: '上传第一份讲义后，学生就能检索它',
    emptyForStudent: '请等本班教师上传讲义',
    columnTitle: '标题',
    columnSize: '大小',
    columnChunks: '切片',
    columnStatus: '状态',
    columnCreatedAt: '上传时间',
    columnActions: '操作',
    status: {
      pending: '排队中',
      processing: '处理中',
      ready: '可检索',
      failed: '处理失败',
    },
    processingHint: '处理中，暂不可检索',
    failedReason: '失败原因',
    chunkCount: '共 {count} 个切片',
    openDetail: '查看切片',
    download: '下载原文',
    delete: '删除',
    deleteConfirm: '删除后本班将检索不到这份资料，确定吗？',
    detailTitle: '资料详情',
    detailChunks: '切片列表',
    backToList: '返回列表',
    chunkRange: '原文第 {start}–{end} 字符',
    uploadDone: '已上传，正在后台切分与入库',
    uploadRejected: '上传被拒绝',
    pagePrev: '上一页',
    pageNext: '下一页',
    pageInfo: '第 {page} / {pages} 页，共 {total} 条',
  },

  search: {
    title: '检索本班资料',
    description: '三种模式：关键词（不调模型）、向量（按意思找）、混合（默认，两路融合）。',
    placeholder: '例如：主定理怎么用递归树证明',
    mode: '模式',
    modes: {
      keyword: '关键词',
      vector: '向量',
      hybrid: '混合',
    },
    submit: '检索',
    searching: '检索中…',
    score: '相关度 {score}',
    hitLocation: '第 {index} 个切片',
    resultCount: '命中 {count} 条',
    tooShort: '查询串至少 2 个字符',
    examplesLabel: '试着搜',
    examples: ['主定理怎么用递归树证明', 'B 树什么情况下分裂', '贪心选择的交换论证'],
    idleTitle: '输入问题，只在本班资料里找答案',
    idleText: '未命中时会明确告诉你「资料中未找到相关内容」，不会编造。',
    modeHint: {
      keyword: '只做词面匹配，不调用向量库',
      vector: '按语义相似度召回，容忍换个说法',
      hybrid: '两路召回融合，默认模式',
    },
  },

  error: {
    network: '网络不可达，请检查服务是否已启动',
    unknown: '发生未知错误，请稍后重试',
    unauthorized: '未登录或会话已过期',
    notFound: '资源不存在',
  },

  /** 检索无命中时的固定文案（RT-08，不得由模型自由生成） */
  retrieval: {
    noHit: '资料中未找到相关内容',
    noHitActionSearch: '换个关键词再试',
    noHitActionUpload: '请教师补充资料',
  },
} as const
