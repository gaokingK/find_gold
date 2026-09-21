import { bloggers, funds, history, initialPositions } from './data'
import type { BloggerDetail, FundOption, InitialPositionRecord, ScreenshotImportResult } from '../types/domain'

export const mockStore = {
  bloggers,
  funds,
  history,
  initialPositions,
  nextScreenshotId: 9100,
  nextBloggerId: 10,
  nextFundId: 110,
}

export function findBlogger(id: number): BloggerDetail | undefined {
  return mockStore.bloggers.find((blogger) => blogger.id === id)
}

export function cloneHistory(): ScreenshotImportResult[] {
  return mockStore.history.map((item) => ({ ...item, records: item.records.map((record) => ({ ...record })) }))
}

export function cloneFunds(): FundOption[] {
  return mockStore.funds.map((fund) => ({ ...fund }))
}

export function cloneInitialPositions(): InitialPositionRecord[] {
  return mockStore.initialPositions.map((position) => ({ ...position }))
}
