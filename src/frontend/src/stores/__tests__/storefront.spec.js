import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { api, getStoreSlug, setStoreSlug } from '@/api/client'
import { useStorefrontStore } from '@/stores/storefront'

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual('@/api/client')
  return {
    ...actual,
    api: vi.fn(),
  }
})

describe('storefront store', () => {
  beforeEach(() => {
    setStoreSlug('')
    document.title = 'pyStore'
  })

  it("sends the bootstrap's store slug with the following requests", async () => {
    setActivePinia(createPinia())
    const store = useStorefrontStore()
    api.mockResolvedValueOnce({ store: { slug: 'main-store', name: 'Main Store' } })
    api.mockResolvedValueOnce({ lines: [], subtotal: '0.0000', total: '0.0000' })

    await store.init()

    expect(api).toHaveBeenCalledWith('/storefront/bootstrap')
    expect(api).toHaveBeenCalledWith('/cart')
    expect(store.store.slug).toBe('main-store')
    expect(getStoreSlug()).toBe('main-store')
  })
})
