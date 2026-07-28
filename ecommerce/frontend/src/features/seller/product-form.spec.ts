import type { SellerAttribute } from '@/features/product/types'

import { generateVariantDrafts, validateVariantDrafts } from './product-form'

const attributes: SellerAttribute[] = [
  {
    id: 'color',
    name: 'Màu',
    code: 'color',
    display_type: 'color',
    sort_order: 0,
    scope: 'global',
    values: [
      { id: 'red', value: 'Đỏ', display_value: null, color_code: '#f00', sort_order: 0 },
      { id: 'blue', value: 'Xanh', display_value: null, color_code: '#00f', sort_order: 1 },
    ],
  },
  {
    id: 'size',
    name: 'Size',
    code: 'size',
    display_type: 'text',
    sort_order: 1,
    scope: 'global',
    values: [
      { id: 's', value: 'S', display_value: null, color_code: null, sort_order: 0 },
      { id: 'm', value: 'M', display_value: null, color_code: null, sort_order: 1 },
    ],
  },
]

describe('seller product variant matrix', () => {
  it('generates the cartesian product of selected values', () => {
    const drafts = generateVariantDrafts(attributes, {
      color: ['red', 'blue'],
      size: ['s', 'm'],
    })
    expect(drafts).toHaveLength(4)
    expect(drafts.map((draft) => draft.label)).toEqual(['Đỏ / S', 'Đỏ / M', 'Xanh / S', 'Xanh / M'])
  })

  it('preserves edited fields when the selection is rebuilt', () => {
    const first = generateVariantDrafts(attributes, { color: ['red'], size: ['s'] })
    first[0]!.sku = 'RED-S'
    const rebuilt = generateVariantDrafts(
      attributes,
      { color: ['red', 'blue'], size: ['s'] },
      first,
    )
    expect(rebuilt.find((draft) => draft.label === 'Đỏ / S')?.sku).toBe('RED-S')
  })

  it('rejects duplicate SKU and invalid prices before API submission', () => {
    const drafts = generateVariantDrafts(attributes, { color: ['red', 'blue'], size: ['s'] })
    for (const draft of drafts) {
      draft.sku = 'DUPLICATE'
      draft.originalPrice = '100000'
      draft.salePrice = '90000'
    }
    expect(validateVariantDrafts(drafts)).toContain('bị trùng')
  })

  it('allows backend-generated SKU and rejects negative stock', () => {
    const drafts = generateVariantDrafts(attributes, { color: ['red'], size: ['s'] })
    drafts[0]!.originalPrice = '100000'
    drafts[0]!.salePrice = '90000'
    expect(validateVariantDrafts(drafts)).toBeNull()

    drafts[0]!.salePrice = '100001'
    expect(validateVariantDrafts(drafts)).toContain('Giá bán')
  })
})
