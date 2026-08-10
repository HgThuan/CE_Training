import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'

import { orderApi } from '@/features/order/api'

import PaymentReturnPage from './PaymentReturnPage.vue'

const routeQuery: Record<string, string> = {}

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery }),
}))

vi.mock('@/features/order/api', () => ({
  orderApi: {
    paymentStatus: vi.fn(),
    verifyVnpayReturn: vi.fn(),
  },
}))

describe('PaymentReturnPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    Object.keys(routeQuery).forEach((key) => delete routeQuery[key])
  })

  it('verifies the signed VNPay return before reading the payment status', async () => {
    Object.assign(routeQuery, {
      vnp_Amount: '10000000',
      vnp_ResponseCode: '00',
      vnp_SecureHash: 'signed-value',
      vnp_TxnRef: 'PAY123',
    })
    localStorage.setItem('last_payment_order_id', 'stale-order-id')
    vi.mocked(orderApi.verifyVnpayReturn).mockResolvedValue({
      data: { order_id: 'paid-order-id', payment_status: 'PAID' },
    } as never)
    vi.mocked(orderApi.paymentStatus).mockResolvedValue({
      data: { data: { payment_status: 'PAID' } },
    } as never)

    const wrapper = mount(PaymentReturnPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    expect(orderApi.verifyVnpayReturn).toHaveBeenCalledWith({
      vnp_Amount: '10000000',
      vnp_ResponseCode: '00',
      vnp_SecureHash: 'signed-value',
      vnp_TxnRef: 'PAY123',
    })
    expect(orderApi.paymentStatus).toHaveBeenCalledWith('paid-order-id')
    expect(wrapper.text()).toContain('Trạng thái thanh toán: Thành công')
    expect(localStorage.getItem('last_payment_order_id')).toBeNull()

    wrapper.unmount()
  })
})
