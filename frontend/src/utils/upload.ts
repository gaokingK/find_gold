const ACCEPTED_TYPES = ['image/png', 'image/jpeg']
const MAX_FILE_SIZE = 10 * 1024 * 1024

export function validateScreenshotFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) return '仅支持 PNG、JPG、JPEG 图片'
  if (file.size > MAX_FILE_SIZE) return '单个文件不能超过 10MB'
  return null
}

export function todayString(): string {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
