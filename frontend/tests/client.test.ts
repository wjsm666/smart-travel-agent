import { afterEach, expect, it, vi } from 'vitest'
import { requestJson } from '../src/api/client'

afterEach(() => vi.unstubAllGlobals())
it('返回后端可读错误，非 JSON 错误和网络故障使用通用提示', async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'VALIDATION_ERROR', message: '景点重复。' }), { status: 422 }))
    .mockResolvedValueOnce(new Response('<html>private upstream details</html>', { status: 502 }))
    .mockRejectedValueOnce(new Error('private network details'))
  vi.stubGlobal('fetch', fetcher)
  await expect(requestJson('/api/plans/validate')).rejects.toThrow('景点重复。')
  await expect(requestJson('/api/plans/validate')).rejects.toThrow('请求未能完成，请稍后重试。')
  await expect(requestJson('/api/plans/validate')).rejects.toThrow('无法连接服务')
})

it('处理成功 JSON、204、无效成功内容和取消请求', async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(new Response('{"items":[]}'))
    .mockResolvedValueOnce(new Response(null, { status: 204 }))
    .mockResolvedValueOnce(new Response('not json'))
    .mockRejectedValueOnce(new DOMException('aborted', 'AbortError'))
  vi.stubGlobal('fetch', fetcher)
  expect(await requestJson('/api/attractions')).toEqual({ items: [] })
  expect(await requestJson('/api/trips/id', { method: 'DELETE' })).toBeUndefined()
  await expect(requestJson('/api/attractions')).rejects.toThrow('服务返回的数据无法读取')
  await expect(requestJson('/api/attractions')).rejects.toMatchObject({ name: 'AbortError' })
})
