import { mount } from '@vue/test-utils'

import HomePage from './HomePage.vue'

describe('HomePage', () => {
  it('renders the dynamic home content boundary', () => {
    const wrapper = mount(HomePage, {
      global: {
        stubs: {
          HomePageContent: {
            template: '<section>Trang chủ động</section>',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('Trang chủ động')
  })
})
