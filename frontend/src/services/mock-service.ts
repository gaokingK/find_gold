import { cloneFunds, cloneHistory, cloneInitialPositions, findBlogger, mockStore } from '../mocks/store'
import type { BloggerDetail, BloggerSummary, FundOption, ParsedOcrRecord, Position, ScreenshotImportResult } from '../types/domain'
import type { BloggerDraft, BloggerQuery, InitialPositionDraft, ServiceAdapter } from './types'

const wait = <T>(value: T): Promise<T> => new Promise((resolve) => window.setTimeout(() => resolve(value), 160))

const summaryOf = (blogger: BloggerDetail): BloggerSummary => ({
  id: blogger.id,
  name: blogger.name,
  sector: blogger.sector,
  observeStartDate: blogger.observeStartDate,
  observeDays: blogger.observeDays,
  status: blogger.status,
  returnRate: blogger.returnRate,
  profit: blogger.profit,
  maxDrawdown: blogger.maxDrawdown,
  operationCount: blogger.operationCount,
})

const cloneDetail = (blogger: BloggerDetail): BloggerDetail => ({
  ...summaryOf(blogger),
  positions: blogger.positions.map((position) => ({ ...position })),
  operations: blogger.operations.map((operation) => ({ ...operation })),
  monthlyOperationCount: blogger.monthlyOperationCount.map((item) => ({ ...item })),
})

const mockService: ServiceAdapter = {
  async listBloggers(query = {}) {
    const keyword = query.keyword?.trim().toLowerCase()
    const filtered = mockStore.bloggers.filter((blogger) => {
      const matchesKeyword = !keyword || blogger.name.toLowerCase().includes(keyword)
      const matchesSector = !query.sector || query.sector === 'all' || blogger.sector === query.sector
      const matchesStatus = !query.status || query.status === 'all' || blogger.status === query.status
      return matchesKeyword && matchesSector && matchesStatus
    })
    const sortValue = (blogger: BloggerDetail): number => {
      if (query.sortBy === 'observeDays') return blogger.observeDays
      if (query.sortBy === 'profit') return blogger.profit ?? Number.NEGATIVE_INFINITY
      return blogger.returnRate ?? Number.NEGATIVE_INFINITY
    }
    const sorted = [...filtered].sort((left, right) => sortValue(right) - sortValue(left))
    return wait(sorted.map(summaryOf))
  },
  async getBloggerDetail(id) {
    const blogger = findBlogger(id)
    if (!blogger) throw new Error('找不到该博主')
    return wait(cloneDetail(blogger))
  },
  async listSectors() {
    return wait([...new Set(mockStore.bloggers.map((blogger) => blogger.sector))])
  },
  async listHistory(operationDate) {
    const items = cloneHistory().filter((item) => !operationDate || item.operationDate === operationDate)
    return wait(items)
  },
  async listFunds() {
    return wait(cloneFunds())
  },
  async listInitialPositions(bloggerId) {
    return wait(cloneInitialPositions().filter((position) => !bloggerId || position.bloggerId === bloggerId))
  },
  async recognizeScreenshot(file, operationDate) {
    const screenshotId = mockStore.nextScreenshotId++
    const result: ScreenshotImportResult = {
      screenshotId,
      fileName: file.name,
      operationDate,
      rawText: `截图文件：${file.name}\n操作日期：${operationDate}\n基金小星 华夏成长混合 申购 5000.00\n慢慢变富 中欧医疗健康混合 申购 2500.00`,
      records: [
        { id: `${screenshotId}-1`, bloggerName: '基金小星', sector: '成长股', fundName: '华夏成长混合', operationAmount: 5000, holdingProfit: 2160, cumulativeProfit: 5674, return1y: 0.1568, return3y: null, maxDrawdown: -0.0823, suspectedDuplicate: false, reviewAction: 'pending' },
        { id: `${screenshotId}-2`, bloggerName: '慢慢变富', sector: '稳健配置', fundName: '中欧医疗健康混合', operationAmount: 2500, holdingProfit: -270, cumulativeProfit: null, return1y: null, return3y: null, maxDrawdown: null, suspectedDuplicate: true, reviewAction: 'pending' },
      ],
    }
    mockStore.history.push(result)
    return wait({ ...result, records: result.records.map((record) => ({ ...record })) })
  },
  async confirmOcrRecords(screenshotId, records) {
    const screenshot = mockStore.history.find((item) => item.screenshotId === screenshotId)
    if (!screenshot) throw new Error('找不到待确认的截图记录')
    screenshot.records = records.map((record) => ({ ...record }))
    const accepted = records.filter((record) => record.reviewAction === 'accepted').length
    const rejected = records.filter((record) => record.reviewAction === 'rejected').length
    return wait({ accepted, rejected })
  },
  async createBlogger(draft: BloggerDraft) {
    const blogger: BloggerDetail = { id: mockStore.nextBloggerId++, ...draft, observeDays: 0, status: 'observing', returnRate: null, profit: null, maxDrawdown: null, operationCount: 0, positions: [], operations: [], monthlyOperationCount: [] }
    mockStore.bloggers.push(blogger)
    return wait(summaryOf(blogger))
  },
  async updateBlogger(id, draft) {
    const blogger = findBlogger(id)
    if (!blogger) throw new Error('找不到该博主')
    Object.assign(blogger, draft)
    return wait(summaryOf(blogger))
  },
  async deleteBlogger(id) {
    const index = mockStore.bloggers.findIndex((blogger) => blogger.id === id)
    if (index < 0) throw new Error('找不到该博主')
    mockStore.bloggers.splice(index, 1)
    await wait(undefined)
  },
  async createFund(draft) {
    const fund = { ...draft, id: mockStore.nextFundId++ }
    mockStore.funds.push(fund)
    return wait(fund)
  },
  async updateFund(id, draft) {
    const fund = mockStore.funds.find((item) => item.id === id)
    if (!fund) throw new Error('找不到该基金')
    Object.assign(fund, draft, { id })
    return wait({ ...fund })
  },
  async createInitialPosition(draft: InitialPositionDraft) {
    const blogger = findBlogger(draft.bloggerId)
    const fund = mockStore.funds.find((item) => item.id === draft.fundId)
    if (!blogger || !fund) throw new Error('博主或基金不存在')
    const position: Position = { fundId: fund.id, fundName: fund.name, fundCode: fund.code, shares: draft.shares, costBasis: draft.costBasis, currentNav: 1, marketValue: draft.costBasis, profit: 0, allocation: 1 }
    const record = { ...position, bloggerId: blogger.id, bloggerName: blogger.name, recordDate: draft.recordDate }
    mockStore.initialPositions.push(record)
    blogger.positions.push(position)
    return wait(record)
  },
}

export default mockService
