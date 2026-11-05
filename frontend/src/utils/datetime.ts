/**
 * 时间展示。后端一律 UTC ISO 串，展示统一在这里转成本地时间，
 * 页面不各自实现——否则同一行数据会在两个页面显示成两种格式。
 */

export function formatDateTime(iso: string): string {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return iso

  const pad = (value: number): string => String(value).padStart(2, '0')
  const date = `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}`
  return `${date} ${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}
