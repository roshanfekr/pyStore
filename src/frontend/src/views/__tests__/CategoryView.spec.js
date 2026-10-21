import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import CategoryView from '@/views/CategoryView.vue'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'tools' } }),
}))

const CATEGORY = {
  id: 3,
  name: 'Tools',
  slug: 'tools',
  description: 'Handy tools.',
  parent: null,
  is_active: true,
  ordering: 0,
}

function mountCategory() {
  setActivePinia(createPinia())
  return mount(CategoryView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
      },
    },
  })
}

describe('CategoryView', () => {
  beforeEach(() => {
    document.title = 'pyStore'
  })

  it('shows a loading state while the category is fetched', async () => {
    let resolve
    api.mockReturnValueOnce(new Promise((r) => { resolve = r }))
    const wrapper = mountCategory()
    expect(wrapper.text()).toContain('Loading category')
    resolve(CATEGORY)
    await vi.waitFor(() => expect(wrapper.text()).toContain('Tools'))
  })

  it('shows the category, its products and its SEO metadata', async () => {
    api.mockResolvedValueOnce(CATEGORY)
    api.mockResolvedValueOnce({
      results: [{ id: 9, name: 'Hammer', slug: 'hammer', price: '15.0000' }],
    })
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Handy tools.'))
    expect(wrapper.text()).toContain('Hammer')
    expect(wrapper.text()).toContain('15.0000')
    expect(wrapper.text()).toContain('1 items')
    expect(document.title).toBe('Tools')
    expect(document.querySelector('meta[name="description"]').getAttribute('content')).toBe(
      'Handy tools.',
    )
  })

  it('links products to the server-rendered product page', async () => {
    api.mockResolvedValueOnce(CATEGORY)
    api.mockResolvedValueOnce({
      results: [{ id: 9, name: 'Hammer', slug: 'hammer', price: '15.0000' }],
    })
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.find('a[href="/product/hammer/"]').exists()).toBe(true))
  })

  it('shows an unavailable state for an unknown category', async () => {
    const error = new Error('Not found')
    error.status = 404
    api.mockRejectedValueOnce(error)
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.text()).toContain('This category is not available'))
  })

  it('shows an unavailable state for an inactive category', async () => {
    api.mockResolvedValueOnce({ ...CATEGORY, is_active: false })
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.text()).toContain('This category is not available'))
  })

  it('shows the error message when the API fails', async () => {
    api.mockRejectedValueOnce(new Error('Request failed (500)'))
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Request failed (500)'))
  })

  it('shows an empty state when the category has no products', async () => {
    api.mockResolvedValueOnce(CATEGORY)
    api.mockResolvedValueOnce({ results: [] })
    const wrapper = mountCategory()
    await vi.waitFor(() => expect(wrapper.text()).toContain('No products in this category yet'))
  })
})
