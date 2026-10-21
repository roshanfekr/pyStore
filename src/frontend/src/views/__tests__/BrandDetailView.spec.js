import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import BrandDetailView from '@/views/BrandDetailView.vue'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'acme' } }),
}))

const BRAND = {
  id: 1,
  name: 'Acme',
  slug: 'acme',
  description: 'Acme makes everything.',
  logo: '',
  effective_meta_title: 'Acme | Official Store',
  effective_meta_description: 'Buy Acme products.',
}

function mountDetail() {
  setActivePinia(createPinia())
  return mount(BrandDetailView, {
    global: {
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
      },
    },
  })
}

describe('BrandDetailView', () => {
  beforeEach(() => {
    document.title = 'pyStore'
  })

  it('shows a loading state while the brand is fetched', async () => {
    let resolve
    api.mockReturnValueOnce(new Promise((r) => { resolve = r }))
    const wrapper = mountDetail()
    expect(wrapper.text()).toContain('Loading brand')
    resolve(BRAND)
    await vi.waitFor(() => expect(wrapper.text()).toContain('Acme'))
  })

  it('shows the brand, its products and its SEO metadata', async () => {
    api.mockResolvedValueOnce(BRAND)
    api.mockResolvedValueOnce({
      results: [{ id: 7, name: 'Acme Product', slug: 'acme-product', price: '10.0000' }],
    })
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Acme makes everything.'))
    expect(wrapper.text()).toContain('Acme Product')
    expect(wrapper.text()).toContain('10.0000')
    expect(document.title).toBe('Acme | Official Store')
    expect(document.querySelector('meta[name="description"]').getAttribute('content')).toBe(
      'Buy Acme products.',
    )
  })

  it('links products to the product page', async () => {
    api.mockResolvedValueOnce(BRAND)
    api.mockResolvedValueOnce({
      results: [{ id: 7, name: 'Acme Product', slug: 'acme-product', price: '10.0000' }],
    })
    const wrapper = mountDetail()
    await vi.waitFor(() =>
      expect(wrapper.find('a[href="/product/acme-product/"]').exists()).toBe(true),
    )
  })

  it('falls back to the brand name and description for the SEO metadata', async () => {
    api.mockResolvedValueOnce({ ...BRAND, effective_meta_title: 'Acme', effective_meta_description: 'Acme makes everything.' })
    api.mockResolvedValueOnce({ results: [] })
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Acme makes everything.'))
    expect(document.title).toBe('Acme')
  })

  it('shows an unavailable state for an unknown or inactive brand', async () => {
    const error = new Error('Not found')
    error.status = 404
    api.mockRejectedValueOnce(error)
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.text()).toContain('This brand is not available'))
  })

  it('shows the error message when the API fails', async () => {
    api.mockRejectedValueOnce(new Error('Request failed (500)'))
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Request failed (500)'))
  })

  it('shows an empty state when the brand has no products', async () => {
    api.mockResolvedValueOnce(BRAND)
    api.mockResolvedValueOnce({ results: [] })
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.text()).toContain('No products in this brand yet'))
  })

  it('falls back to the initial when the brand has no logo', async () => {
    api.mockResolvedValueOnce(BRAND)
    api.mockResolvedValueOnce({ results: [] })
    const wrapper = mountDetail()
    await vi.waitFor(() => expect(wrapper.find('.brand-logo-fallback').exists()).toBe(true))
    expect(wrapper.find('img.brand-logo-image').exists()).toBe(false)
  })
})
