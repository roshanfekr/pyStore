import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import ProductDetailView from '@/views/ProductDetailView.vue'
import { api } from '@/api/client'

vi.mock('@/api/client', () => ({
  api: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'hammer' } }),
}))

const PRODUCT = {
  id: 9,
  name: 'Hammer',
  slug: 'hammer',
  description: 'A sturdy hammer.',
  product_type: 'simple',
  sku: 'HAM-1',
  category: { slug: 'tools', name: 'Tools' },
  brand: { slug: 'acme', name: 'Acme' },
  images: [],
  options: [],
  variants: [],
  selected_variant: '',
  price: '100 تومان',
  price_value: '100.0000',
  compare_at_price: '',
  in_stock: true,
  available_quantity: 10,
  currency: { code: 'IRT', symbol: 'تومان', decimal_places: 0 },
  meta_title: 'Hammer',
  meta_description: 'A sturdy hammer.',
}

function variant(sku, color, size, price, inStock, quantity, image = '') {
  return {
    id: sku.length,
    sku,
    price,
    price_value: price,
    compare_at_price: '',
    image,
    in_stock: inStock,
    available_quantity: quantity,
    attributes: { color, size },
    is_default: false,
  }
}

const VARIANT_PRODUCT = {
  ...PRODUCT,
  id: 10,
  name: 'Shirt',
  slug: 'shirt',
  product_type: 'variant',
  sku: '',
  images: [
    { id: 1, url: '/media/catalog/products/shirt.png', alt: 'Shirt', position: 0, is_main: true },
    { id: 2, url: '/media/catalog/products/shirt-2.png', alt: '', position: 1, is_main: false },
  ],
  options: [
    {
      name: 'Color',
      slug: 'color',
      type: 'color',
      values: [
        { value: '#ff0000', label: '#ff0000', swatch: '#ff0000', available: true },
        { value: '#0000ff', label: '#0000ff', swatch: '#0000ff', available: false },
        { value: '#00ff00', label: '#00ff00', swatch: '#00ff00', available: true },
      ],
    },
    {
      name: 'Size',
      slug: 'size',
      type: 'size',
      values: [
        { value: 'M', label: 'M', swatch: null, available: true },
        { value: 'L', label: 'L', swatch: null, available: true },
      ],
    },
  ],
  variants: [
    variant('SHIRT-RED-M', '#ff0000', 'M', '120 تومان', true, 4, '/media/catalog/variants/red.png'),
    variant('SHIRT-BLUE-M', '#0000ff', 'M', '90 تومان', false, 0),
    variant('SHIRT-RED-L', '#ff0000', 'L', '130 تومان', true, 2),
    variant('SHIRT-GREEN-L', '#00ff00', 'L', '140 تومان', true, 1),
  ],
  selected_variant: 'SHIRT-RED-M',
  price: '120 تومان',
  in_stock: true,
  available_quantity: 0,
}

function mountProduct() {
  setActivePinia(createPinia())
  return mount(ProductDetailView, {
    global: {
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
      },
    },
  })
}

describe('ProductDetailView', () => {
  beforeEach(() => {
    document.title = 'pyStore'
  })

  it('shows a loading state while the product is fetched', async () => {
    let resolve
    api.mockReturnValueOnce(new Promise((r) => { resolve = r }))
    const wrapper = mountProduct()
    expect(wrapper.text()).toContain('Loading product')
    resolve(PRODUCT)
    await vi.waitFor(() => expect(wrapper.text()).toContain('Hammer'))
  })

  it('shows the product information and its SEO metadata', async () => {
    api.mockResolvedValueOnce(PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('A sturdy hammer.'))

    expect(wrapper.text()).toContain('Hammer')
    expect(wrapper.text()).toContain('100 تومان')
    expect(wrapper.text()).toContain('HAM-1')
    expect(wrapper.text()).toContain('In stock')
    expect(wrapper.text()).toContain('Acme')
    expect(wrapper.text()).toContain('Tools')
    expect(document.title).toBe('Hammer')
    expect(document.querySelector('meta[name="description"]').getAttribute('content')).toBe(
      'A sturdy hammer.',
    )
  })

  it('shows the product images', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.find('img.product-detail-image').exists()).toBe(true))
    // The selected combination's own image leads the gallery (FR-CAT-002).
    expect(wrapper.find('img.product-detail-image').attributes('src')).toBe(
      '/media/catalog/variants/red.png',
    )
    expect(wrapper.findAll('.product-detail-thumb')).toHaveLength(3)
  })

  it('falls back to the product images when the variant has no image', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.find('img.product-detail-image').exists()).toBe(true))

    await wrapper.find('#variant-select').setValue('SHIRT-RED-L')

    expect(wrapper.find('img.product-detail-image').attributes('src')).toBe(
      '/media/catalog/products/shirt.png',
    )
  })

  it('falls back to the initial when the product has no image', async () => {
    api.mockResolvedValueOnce(PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.find('.product-media-fallback').exists()).toBe(true))
    expect(wrapper.find('img.product-detail-image').exists()).toBe(false)
    expect(wrapper.find('.product-media-fallback').text()).toBe('H')
  })

  it('shows the variant combinations and selects the default one', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    expect(wrapper.text()).toContain('120 تومان')
    expect(wrapper.text()).toContain('In stock')
    expect(wrapper.find('#variant-select').element.value).toBe('SHIRT-RED-M')
    expect(wrapper.findAll('.product-option-values .swatch')).toHaveLength(3)
    expect(wrapper.findAll('.product-option-values .option-pill')).toHaveLength(2)
  })

  it('updates the price, the SKU and the availability when a variant is selected', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    await wrapper.find('#variant-select').setValue('SHIRT-BLUE-M')

    expect(wrapper.text()).toContain('90 تومان')
    expect(wrapper.text()).toContain('SHIRT-BLUE-M')
    expect(wrapper.text()).toContain('Out of stock')
    expect(wrapper.find('.btn').attributes('disabled')).toBeDefined()
  })

  it('updates the price when an option combination is selected', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    const sizePills = wrapper.findAll('.product-option-values .option-pill')
    await sizePills[1].trigger('click')

    expect(wrapper.text()).toContain('130 تومان')
    expect(wrapper.text()).toContain('SHIRT-RED-L')
  })

  it('refuses a combination that no variant carries', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    // Green is only available in size L, so green + M is not a combination.
    const swatches = wrapper.findAll('.product-option-values .swatch')
    await swatches[2].trigger('click')

    expect(wrapper.text()).toContain('This combination is not available.')
    expect(wrapper.find('.btn').attributes('disabled')).toBeDefined()
  })

  it('disables the add to cart button for an out of stock product', async () => {
    api.mockResolvedValueOnce({ ...PRODUCT, in_stock: false, available_quantity: 0 })
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Out of stock'))
    expect(wrapper.find('.btn').attributes('disabled')).toBeDefined()
  })

  it('adds the selected variant to the cart', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    api.mockResolvedValueOnce({ lines: [], subtotal: '0.0000', total: '0.0000' })
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    await wrapper.find('.btn').trigger('click')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Added to cart.'))
    expect(api).toHaveBeenCalledWith('/cart/items', {
      method: 'POST',
      body: { product: 'shirt', quantity: 1, variant: 'SHIRT-RED-M' },
    })
  })

  it('shows the error the cart API returns', async () => {
    api.mockResolvedValueOnce(VARIANT_PRODUCT)
    api.mockRejectedValueOnce(new Error('Only 2 item(s) available'))
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('SHIRT-RED-M'))

    await wrapper.find('.btn').trigger('click')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Only 2 item(s) available'))
    expect(wrapper.text()).not.toContain('Added to cart.')
  })

  it('shows an unavailable state for an unknown product', async () => {
    const error = new Error('Not found')
    error.status = 404
    api.mockRejectedValueOnce(error)
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('This product is not available'))
  })

  it('shows the error message when the API fails', async () => {
    api.mockRejectedValueOnce(new Error('Request failed (500)'))
    const wrapper = mountProduct()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Request failed (500)'))
  })
})
