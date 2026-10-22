import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, getStoreSlug, setStoreSlug } from '@/api/client'

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear()
    document.cookie = 'csrftoken=;expires=Thu, 01 Jan 1970 00:00:00 GMT'
    setStoreSlug('')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the store slug as the X-Store header once it is known', async () => {
    const fetch = vi.fn(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetch)
    setStoreSlug('store-a')

    await api('/cart')

    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][1].headers['X-Store']).toBe('store-a')
    expect(getStoreSlug()).toBe('store-a')
  })

  it('does not send a store header before the bootstrap provides one', async () => {
    const fetch = vi.fn(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetch)

    await api('/storefront/bootstrap')

    expect(fetch.mock.calls[0][1].headers['X-Store']).toBeUndefined()
  })

  it('lets a per-call store header win', async () => {
    const fetch = vi.fn(async () => jsonResponse({}))
    vi.stubGlobal('fetch', fetch)
    setStoreSlug('store-a')

    await api('/cart', { headers: { 'X-Store': 'store-b' } })

    expect(fetch.mock.calls[0][1].headers['X-Store']).toBe('store-b')
  })
})
