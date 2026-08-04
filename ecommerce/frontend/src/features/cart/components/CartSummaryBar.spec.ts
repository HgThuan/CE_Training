import { mount } from '@vue/test-utils'

import CartSummaryBar from './CartSummaryBar.vue'

describe('CartSummaryBar checkout navigation', () => {
  it('shows the automatic subtotal and exposes checkout', async () => {
    const wrapper = mount(CartSummaryBar, {
      props: {
        selectedCount: 1,
        selectedTotal: 120_000,
        disabled: false,
      },
    })

    const buttons = wrapper.findAll('button')
    expect(wrapper.text()).toContain('120.000')
    expect(buttons.map((button) => button.text())).toEqual(['Tiến hành thanh toán'])

    await buttons[0].trigger('click')
    expect(wrapper.emitted('checkout')).toHaveLength(1)
  })

  it('disables checkout when no valid item is selected', () => {
    const wrapper = mount(CartSummaryBar, {
      props: {
        selectedCount: 0,
        selectedTotal: 0,
        disabled: true,
      },
    })

    expect(wrapper.findAll('button').every((button) => button.attributes('disabled') !== undefined))
      .toBe(true)
  })
})
