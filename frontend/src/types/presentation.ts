export type VisualTone = 'default' | 'positive' | 'negative' | 'muted' | 'warning' | 'error'

export type AsyncState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

export type FeedbackKind = 'success' | 'error' | 'warning' | 'info'

export interface PageFeedback {
  kind: FeedbackKind
  title: string
  description?: string
}

export interface NavItem {
  path: string
  label: string
  icon: string
  ariaLabel?: string
}

export interface PageRouteMetadata {
  path: string
  title: string
  pathLabel: string
}

export interface AsyncStatePresentation {
  tone: VisualTone
  label: string
  icon: string
}
