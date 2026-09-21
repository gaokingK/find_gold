import type {
  BloggerDetail,
  BloggerStatus,
  BloggerSummary,
  FundOption,
  InitialPositionRecord,
  ParsedOcrRecord,
  Position,
  ScreenshotImportResult,
} from '../types/domain'

export interface BloggerQuery {
  sector?: string
  status?: BloggerStatus | 'all'
  keyword?: string
  sortBy?: 'returnRate' | 'observeDays' | 'profit'
}

export interface BloggerDraft {
  name: string
  sector: string
  observeStartDate: string
}

export interface InitialPositionDraft {
  bloggerId: number
  fundId: number
  shares: number
  costBasis: number
  recordDate: string
}

export interface ServiceAdapter {
  listBloggers(query?: BloggerQuery): Promise<BloggerSummary[]>
  getBloggerDetail(id: number): Promise<BloggerDetail>
  listSectors(): Promise<string[]>
  listHistory(operationDate?: string): Promise<ScreenshotImportResult[]>
  listFunds(): Promise<FundOption[]>
  listInitialPositions(bloggerId?: number): Promise<Position[]>
  recognizeScreenshot(file: File, operationDate: string): Promise<ScreenshotImportResult>
  confirmOcrRecords(screenshotId: number, records: ParsedOcrRecord[]): Promise<{ accepted: number; rejected: number }>
  createBlogger(draft: BloggerDraft): Promise<BloggerSummary>
  updateBlogger(id: number, draft: BloggerDraft): Promise<BloggerSummary>
  deleteBlogger(id: number): Promise<void>
  createFund(draft: FundOption): Promise<FundOption>
  updateFund(id: number, draft: FundOption): Promise<FundOption>
  createInitialPosition(draft: InitialPositionDraft): Promise<InitialPositionRecord>
}
