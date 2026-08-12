import { mount } from '@vue/test-utils'

import ProductCompareTable from './ProductCompareTable.vue'

const comparison = {
  products: [
    { id: 'one', name: 'Sản phẩm một' },
    { id: 'two', name: 'Sản phẩm hai' },
  ],
  rows: [{ label: 'Giá', values: ['100.000 ₫', '120.000 ₫'] }],
  recommendations: [{ need: 'Tiết kiệm', product_index: 0, reason: 'Có giá bán thấp hơn.' }],
  is_comparable: true,
  compatibility_message: null,
  is_ai_generated: true,
  ai_label: 'Tạo bởi AI',
}

describe('ProductCompareTable', () => {
  it('renders the comparison and AI badge for AI-generated content', () => {
    const wrapper = mount(ProductCompareTable, { props: { comparison } })

    expect(wrapper.text()).toContain('Sản phẩm một')
    expect(wrapper.text()).toContain('100.000 ₫')
    expect(wrapper.text()).toContain('Tạo bởi AI')
  })

  it('does not render the AI badge for rule-based content', () => {
    const wrapper = mount(ProductCompareTable, {
      props: {
        comparison: { ...comparison, is_ai_generated: false, ai_label: null },
      },
    })

    expect(wrapper.text()).not.toContain('Tạo bởi AI')
  })

  it('shows guidance instead of a table for unrelated product groups', () => {
    const wrapper = mount(ProductCompareTable, {
      props: {
        comparison: {
          ...comparison,
          rows: [],
          recommendations: [],
          is_comparable: false,
          compatibility_message:
            'Các sản phẩm thuộc nhóm Điện tử và Thời trang nên không có cùng bộ tiêu chí.',
          is_ai_generated: false,
          ai_label: null,
        },
      },
    })

    expect(wrapper.text()).toContain('Không thể so sánh nhóm sản phẩm này')
    expect(wrapper.text()).toContain('Điện tử và Thời trang')
    expect(wrapper.text()).toContain('Sản phẩm một')
    expect(wrapper.find('table').exists()).toBe(false)
  })
})
