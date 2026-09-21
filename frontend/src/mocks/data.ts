import type { BloggerDetail, FundOption, Operation, Position, ScreenshotImportResult } from '../types/domain'

export const funds: FundOption[] = [
  { id: 101, name: '华夏成长混合', code: '000001' },
  { id: 102, name: '易方达蓝筹精选', code: '005827' },
  { id: 103, name: '中欧医疗健康混合', code: '003095' },
  { id: 104, name: '景顺长城新能源产业', code: '011328' },
]

const positions: Record<number, Position[]> = {
  1: [
    { fundId: 101, fundName: '华夏成长混合', fundCode: '000001', shares: 12000, costBasis: 15600, currentNav: 1.48, marketValue: 17760, profit: 2160, allocation: 0.44 },
    { fundId: 102, fundName: '易方达蓝筹精选', fundCode: '005827', shares: 6800, costBasis: 10200, currentNav: 1.91, marketValue: 12988, profit: 2788, allocation: 0.32 },
    { fundId: 104, fundName: '景顺长城新能源产业', fundCode: '011328', shares: 4200, costBasis: 7800, currentNav: 2.03, marketValue: 8526, profit: 726, allocation: 0.24 },
  ],
  2: [
    { fundId: 103, fundName: '中欧医疗健康混合', fundCode: '003095', shares: 3000, costBasis: 4200, currentNav: 1.31, marketValue: 3930, profit: -270, allocation: 1 },
  ],
  3: [
    { fundId: 103, fundName: '中欧医疗健康混合', fundCode: '003095', shares: 18000, costBasis: 30000, currentNav: 1.42, marketValue: 25560, profit: -4440, allocation: 0.56 },
    { fundId: 104, fundName: '景顺长城新能源产业', fundCode: '011328', shares: 9200, costBasis: 21000, currentNav: 1.16, marketValue: 10672, profit: -10328, allocation: 0.44 },
  ],
}

const operations: Record<number, Operation[]> = {
  1: [
    { id: 1001, bloggerId: 1, fundId: 101, fundName: '华夏成长混合', operationDate: '2026-06-28', operationType: 'buy', amount: 5000, shares: 3400, screenshotId: 9001, reviewAction: 'accepted', suspectedDuplicate: false },
    { id: 1002, bloggerId: 1, fundId: 102, fundName: '易方达蓝筹精选', operationDate: '2026-07-08', operationType: 'sell', amount: 2500, shares: 1300, screenshotId: 9002, reviewAction: 'accepted', suspectedDuplicate: false },
    { id: 1003, bloggerId: 1, fundId: 104, fundName: '景顺长城新能源产业', operationDate: '2026-07-15', operationType: 'buy', amount: 3200, shares: 1600, screenshotId: null, reviewAction: 'pending', suspectedDuplicate: false },
  ],
  2: [],
  3: [
    { id: 3001, bloggerId: 3, fundId: 103, fundName: '中欧医疗健康混合', operationDate: '2026-06-21', operationType: 'buy', amount: 12000, shares: 8200, screenshotId: 9003, reviewAction: 'accepted', suspectedDuplicate: false },
    { id: 3002, bloggerId: 3, fundId: 104, fundName: '景顺长城新能源产业', operationDate: '2026-07-05', operationType: 'buy', amount: 8000, shares: 3500, screenshotId: 9004, reviewAction: 'accepted', suspectedDuplicate: false },
  ],
}

export const bloggers: BloggerDetail[] = [
  { id: 1, name: '基金小星', sector: '成长股', observeStartDate: '2026-03-22', observeDays: 120, status: 'active', returnRate: 0.1568, profit: 5674, maxDrawdown: -0.0823, operationCount: 3, positions: positions[1], operations: operations[1], monthlyOperationCount: [{ month: '2026-04', count: 1 }, { month: '2026-05', count: 0 }, { month: '2026-06', count: 1 }, { month: '2026-07', count: 1 }] },
  { id: 2, name: '慢慢变富', sector: '稳健配置', observeStartDate: '2026-07-02', observeDays: 18, status: 'observing', returnRate: null, profit: null, maxDrawdown: null, operationCount: 0, positions: positions[2], operations: operations[2], monthlyOperationCount: [{ month: '2026-07', count: 0 }] },
  { id: 3, name: '逆向投资者', sector: '行业轮动', observeStartDate: '2026-06-05', observeDays: 45, status: 'active', returnRate: -0.2145, profit: -14768, maxDrawdown: -0.267, operationCount: 2, positions: positions[3], operations: operations[3], monthlyOperationCount: [{ month: '2026-06', count: 1 }, { month: '2026-07', count: 1 }] },
]

export const history: ScreenshotImportResult[] = [
  { screenshotId: 9001, fileName: 'fund-star-0628.png', operationDate: '2026-06-28', rawText: '基金小星\n华夏成长混合 申购 5000.00\n识别来源：本地 Demo mock', records: [{ id: '9001-1', bloggerName: '基金小星', sector: '成长股', fundName: '华夏成长混合', operationAmount: 5000, holdingProfit: 2160, cumulativeProfit: 5674, return1y: 0.1568, return3y: null, maxDrawdown: -0.0823, suspectedDuplicate: false, reviewAction: 'accepted' }] },
  { screenshotId: 9002, fileName: 'fund-star-0708.jpg', operationDate: '2026-07-08', rawText: '基金小星\n易方达蓝筹精选 赎回 2500.00\n识别来源：本地 Demo mock', records: [{ id: '9002-1', bloggerName: '基金小星', sector: '成长股', fundName: '易方达蓝筹精选', operationAmount: 2500, holdingProfit: 2788, cumulativeProfit: 5674, return1y: 0.1568, return3y: null, maxDrawdown: -0.0823, suspectedDuplicate: false, reviewAction: 'accepted' }] },
]

export const initialPositions: Array<Position & { bloggerId: number; bloggerName: string; recordDate: string }> = [
  { ...positions[1][0], bloggerId: 1, bloggerName: '基金小星', recordDate: '2026-03-22' },
  { ...positions[2][0], bloggerId: 2, bloggerName: '慢慢变富', recordDate: '2026-07-02' },
  { ...positions[3][0], bloggerId: 3, bloggerName: '逆向投资者', recordDate: '2026-06-05' },
]
