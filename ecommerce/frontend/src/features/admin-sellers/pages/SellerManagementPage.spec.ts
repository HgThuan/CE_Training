import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import { beforeEach, vi } from 'vitest'

import SellerManagementPage from './SellerManagementPage.vue'

const route = reactive<{ query: Record<string, string> }>({ query: {} })
const replace = vi.fn(async ({ query }: { query: Record<string, string> }) => {
  route.query = query
})

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ replace }),
}))

const global = {
  stubs: {
    ActiveSellerWorkspace: { template: '<div>ACTIVE_WORKSPACE</div>' },
    SellerApplicationWorkspace: {
      props: ['status'],
      template: '<div>APPLICATION_{{ status }}</div>',
    },
  },
}

describe('SellerManagementPage', () => {
  beforeEach(() => {
    route.query = {}
    replace.mockClear()
  })

  it('opens active sellers by default', () => {
    const wrapper = mount(SellerManagementPage, { global })
    expect(wrapper.text()).toContain('ACTIVE_WORKSPACE')
  })

  it('switches to the pending application workspace through the query tab', async () => {
    const wrapper = mount(SellerManagementPage, { global })
    await wrapper.findAll('[role="tab"]')[0]!.trigger('click')
    expect(replace).toHaveBeenCalledWith({ query: { tab: 'pending' } })
    expect(wrapper.text()).toContain('APPLICATION_pending')
  })
})
