/**
 * 全部中文文案的唯一出处。
 *
 * 规范依据：docs/specs/01-产品设计规范.md §5（文案与术语表）
 * 页面里不写字符串字面量——改文案只改这里，避免同一个意思出现三种说法。
 */

export const copy = {
  appName: 'CampusClaw · TeamVibe',
  appTagline: '按班级隔离的课程知识库与解题助手',

  /** 视图四状态：加载中 / 正常 / 错误 / 空状态 */
  viewState: {
    loading: '正在加载…',
    errorTitle: '加载失败',
    errorRetry: '重新加载',
    emptyTitle: '暂无数据',
    emptyDescription: '当前还没有可展示的内容',
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
