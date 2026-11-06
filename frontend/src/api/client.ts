/** Shared fetch boundary for A and B; never display raw response bodies. */
export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch (error) {
    if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error
    throw new Error('无法连接服务，请检查后端是否已启动后重试。')
  }
  if (!response.ok) {
    let message = '请求未能完成，请稍后重试。'
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'message' in body &&
          typeof body.message === 'string' && body.message.trim()) message = body.message
    } catch { /* HTML, invalid JSON and empty error responses use the readable fallback. */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  try {
    return await response.json() as T
  } catch {
    throw new Error('服务返回的数据无法读取，请重试。')
  }
}
