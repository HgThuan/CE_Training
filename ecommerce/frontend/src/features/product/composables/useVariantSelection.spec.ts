import type { ProductAttribute, ProductVariant } from '../types'
import {
  findSelectedVariant,
  isVariantValueAvailable,
  variantMatchesSelection,
} from './useVariantSelection'

const attributes: ProductAttribute[] = [
  {
    id: 'color',
    name: 'Màu',
    code: 'color',
    display_type: 'color',
    values: [
      { id: 'red', value: 'Đỏ', display_value: null, color_code: '#f00', sort_order: 0 },
      { id: 'blue', value: 'Xanh', display_value: null, color_code: '#00f', sort_order: 1 },
    ],
  },
  {
    id: 'size',
    name: 'Kích thước',
    code: 'size',
    display_type: 'text',
    values: [
      { id: 's', value: 'S', display_value: null, color_code: null, sort_order: 0 },
      { id: 'm', value: 'M', display_value: null, color_code: null, sort_order: 1 },
    ],
  },
]

const variants: ProductVariant[] = [
  {
    id: 'red-s',
    sku: 'RED-S',
    name: null,
    original_price: '100000',
    sale_price: '90000',
    weight_grams: null,
    attributes: [
      {
        attribute_id: 'color',
        attribute_name: 'Màu',
        attribute_value_id: 'red',
        value: 'Đỏ',
        display_value: null,
        color_code: '#f00',
      },
      {
        attribute_id: 'size',
        attribute_name: 'Kích thước',
        attribute_value_id: 's',
        value: 'S',
        display_value: null,
        color_code: null,
      },
    ],
  },
  {
    id: 'blue-m',
    sku: 'BLUE-M',
    name: null,
    original_price: '100000',
    sale_price: '95000',
    weight_grams: null,
    attributes: [
      {
        attribute_id: 'color',
        attribute_name: 'Màu',
        attribute_value_id: 'blue',
        value: 'Xanh',
        display_value: null,
        color_code: '#00f',
      },
      {
        attribute_id: 'size',
        attribute_name: 'Kích thước',
        attribute_value_id: 'm',
        value: 'M',
        display_value: null,
        color_code: null,
      },
    ],
  },
]

describe('variant selection', () => {
  it('finds the exact selected combination', () => {
    expect(findSelectedVariant(variants, attributes, { color: 'red', size: 's' })?.id).toBe('red-s')
    expect(findSelectedVariant(variants, attributes, { color: 'red', size: 'm' })).toBeNull()
  })

  it('disables values that cannot complete the current selection', () => {
    expect(isVariantValueAvailable(variants, { color: 'red' }, 'size', 's')).toBe(true)
    expect(isVariantValueAvailable(variants, { color: 'red' }, 'size', 'm')).toBe(false)
  })

  it('can ignore the attribute being changed', () => {
    expect(variantMatchesSelection(variants[1]!, { color: 'red', size: 'm' }, 'color')).toBe(true)
  })
})
