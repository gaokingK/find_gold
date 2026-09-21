export type BloggerStatus = 'active' | 'observing' | 'inactive'
export type OperationType = 'buy' | 'sell'
export type ReviewAction = 'pending' | 'accepted' | 'rejected'

export interface BloggerSummary {
  id: number
  name: string
  sector: string
  observeStartDate: string
  observeDays: number
  status: BloggerStatus
  returnRate: number | null
  profit: number | null
  maxDrawdown: number | null
  operationCount: number
}

export interface Position {
  fundId: number
  fundName: string
  fundCode: string
  shares: number
  costBasis: number
  currentNav: number
  marketValue: number
  profit: number
  allocation: number
}

export interface Operation {
  id: number
  bloggerId: number
  fundId: number
  fundName: string
  operationDate: string
  operationType: OperationType
  amount: number
  shares: number | null
  screenshotId: number | null
  reviewAction: ReviewAction
  suspectedDuplicate: boolean
}

export interface BloggerDetail extends BloggerSummary {
  positions: Position[]
  operations: Operation[]
  monthlyOperationCount: Array<{ month: string; count: number }>
}

export interface ParsedOcrRecord {
  id: string
  bloggerName: string
  sector: string
  fundName: string
  operationAmount: number
  holdingProfit: number | null
  cumulativeProfit: number | null
  return1y: number | null
  return3y: number | null
  maxDrawdown: number | null
  suspectedDuplicate: boolean
  reviewAction: ReviewAction
}

export interface ScreenshotImportResult {
  screenshotId: number
  fileName: string
  operationDate: string
  rawText: string
  records: ParsedOcrRecord[]
}

export interface FundOption {
  id: number
  name: string
  code: string
}

export interface InitialPositionRecord extends Position {
  bloggerId: number
  bloggerName: string
  recordDate: string
}
