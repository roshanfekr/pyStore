import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import BrandListView from '@/views/BrandListView.vue'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: vi.fn(),
}))

const globalMountOptions = {
  stubs: {
    RouterLink: { template: '<a><slot /></a>' },
  },
}

function mountList() {
  setActivePinia(createPinia())
  return mount(BrandListView, { global: globalMountOptions })
}

describe('BrandListView', () => {
  it('shows a loading state while the brands are fetched', async () => {
    let resolve
    api.mockReturnValue(new Promise((r) => { resolve = r }))
    const wrapper = mountList()
    expect(wrapper.text()).toContain('Loading brands')
    resolve({ results: [] })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).not.toContain('Loading brands')
  })

  it('lists the brands returned by the API', async () => {
    api.mockResolvedValue({
      results: [
        { id: 1, name: 'Acme', slug: 'acme', description: 'Acme makes everything.', logo: '' },
        { id: 2, name: 'Globex', slug: 'globex', description: '', logo: '/media/globex.png' },
      ],
    })
    const wrapper = mountList()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Acme'))
    expect(wrapper.text()).toContain('Globex')
    expect(wrapper.text()).toContain('2 brands')
  })

  it('shows an empty state when there are no brands', async () => {
    api.mockResolvedValue({ results: [] })
    const wrapper = mountList()
    await vi.waitFor(() => expect(wrapper.text()).toContain('No brands are available'))
  })

  it('shows the error message when the API fails', async () => {
    api.mockRejectedValue(new Error('Request failed (500)'))
    const wrapper = mountList()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Request failed (500)'))
  })

  it('falls back to the initial when a brand has no logo', async () => {
    api.mockResolvedValue({
      results: [{ id: 1, name: 'Acme', slug: 'acme', description: '', logo: '' }],
    })
    const wrapper = mountList()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Acme'))
    expect(wrapper.find('.brand-logo-fallback').exists()).toBe(true)
    expect(wrapper.find('img.brand-logo-image').exists()).toBe(false)
  })

  it('renders the logo image with an alternative text when one is configured', async () => {
    api.mockResolvedValue({
      results: [{ id: 2, name: 'Globex', slug: 'globex', description: '', logo: '/media/globex.png' }],
    })
    const wrapper = mountList()
    await vi.waitFor(() => expect(wrapper.find('img.brand-logo-image').exists()).toBe(true))
    expect(wrapper.find('img.brand-logo-image').attributes('alt')).toBe('Globex logo')
  })
})
