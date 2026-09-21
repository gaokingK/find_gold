import { valueTone } from './formatters'
import type {
  AsyncState,
  AsyncStatePresentation,
  FeedbackKind,
  NavItem,
  PageFeedback,
  PageRouteMetadata,
  VisualTone,
} from '../types/presentation'

export const navigationItems: readonly NavItem[] = [
  { path: '/', label: '总览', icon: '▦', ariaLabel: '前往总览' },
  { path: '/import', label: '截图导入', icon: '⇧', ariaLabel: '前往截图导入' },
  { path: '/history', label: '历史记录', icon: '◷', ariaLabel: '前往历史记录' },
  { path: '/settings', label: '基础设置', icon: '⚙', ariaLabel: '前往基础设置' },
]

export const pageRouteMetadata: readonly PageRouteMetadata[] = [
  { path: '/', title: '总览', pathLabel: 'FUND TRACKER / OVERVIEW' },
  { path: '/import', title: '截图导入', pathLabel: 'FUND TRACKER / IMPORT' },
  { path: '/history', title: '历史记录', pathLabel: 'FUND TRACKER / HISTORY' },
  { path: '/settings', title: '基础设置', pathLabel: 'FUND TRACKER / SETTINGS' },
  { path: '/bloggers/:id', title: '博主详情', pathLabel: 'FUND TRACKER / BLOGGER' },
]

const asyncStatePresentation: Record<AsyncState, AsyncStatePresentation> = {
  idle: { tone: 'default', label: '尚未开始', icon: '○' },
  loading: { tone: 'default', label: '加载中', icon: '…' },
  success: { tone: 'positive', label: '已完成', icon: '✓' },
  empty: { tone: 'muted', label: '暂无数据', icon: '—' },
  error: { tone: 'error', label: '加载失败', icon: '!' },
}

const feedbackDefaults: Record<FeedbackKind, Omit<PageFeedback, 'kind'>> = {
  success: { title: '操作成功' },
  error: { title: '操作失败', description: '请稍后重试。' },
  warning: { title: '请注意' },
  info: { title: '提示' },
}

export function getVisualTone(value: number | null): VisualTone {
  return valueTone(value)
}

export function getAsyncStatePresentation(state: AsyncState): AsyncStatePresentation {
  return asyncStatePresentation[state]
}

export function getPageFeedback(
  kind: FeedbackKind,
  title = feedbackDefaults[kind].title,
  description = feedbackDefaults[kind].description,
): PageFeedback {
  return { kind, title, ...(description ? { description } : {}) }
}

export function getActiveNavPath(path: string): string {
  return path.startsWith('/bloggers/') ? '/' : path
}

export function isNavItemActive(itemPath: string, currentPath: string): boolean {
  return itemPath === getActiveNavPath(currentPath)
}

export function getPageRouteMetadata(path: string): PageRouteMetadata {
  if (path.startsWith('/bloggers/')) {
    return pageRouteMetadata[pageRouteMetadata.length - 1]
  }

  return pageRouteMetadata.find((metadata) => metadata.path === path) ?? {
    path,
    title: '页面',
    pathLabel: 'FUND TRACKER / PAGE',
  }
}
