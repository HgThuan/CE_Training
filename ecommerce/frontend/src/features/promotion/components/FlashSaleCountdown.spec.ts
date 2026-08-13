import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import FlashSaleCountdown from './FlashSaleCountdown.vue'

describe('FlashSaleCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-31T00:00:00Z'))
  })

  afterEach(() => vi.useRealTimers())

  it('renders remaining time and emits ended after the deadline', async () => {
    const wrapper = mount(FlashSaleCountdown, {
      props: { endTime: '2026-07-31T00:00:02Z' },
    })
    expect(wrapper.text()).toBe('00:00:02')

    await vi.advanceTimersByTimeAsync(2000)

    expect(wrapper.text()).toBe('Đã kết thúc')
    expect(wrapper.emitted('ended')).toHaveLength(1)
  })
})
