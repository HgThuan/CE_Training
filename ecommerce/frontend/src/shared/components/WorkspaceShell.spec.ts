import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import WorkspaceShell from './WorkspaceShell.vue'

describe('WorkspaceShell', () => {
  it('marks the most specific route active and supports keyboard-safe mobile navigation', async () => {
    const icon = { template: '<svg />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/seller', component: { template: '<div />' } },
        { path: '/seller/orders', component: { template: '<div />' } },
      ],
    })
    await router.push('/seller/orders')
    await router.isReady()

    const wrapper = mount(WorkspaceShell, {
      attachTo: document.body,
      props: {
        description: 'Quản lý gian hàng',
        workspace: 'seller',
        workspaceLabel: 'Seller Center',
        navigation: [
          {
            label: '',
            items: [{ label: 'Tổng quan', to: '/seller', icon, exact: true }],
          },
          {
            label: 'Bán hàng',
            items: [{ label: 'Đơn hàng', to: '/seller/orders', icon }],
          },
        ],
      },
      global: {
        plugins: [createPinia(), router],
        stubs: {
          NotificationBell: true,
          RouterView: true,
        },
      },
    })

    const activeLink = wrapper.get('a[href="/seller/orders"]')
    expect(activeLink.classes()).toContain('workspace-navigation__link--active')
    expect(activeLink.attributes('aria-current')).toBe('page')
    expect(wrapper.get('a[href="/seller"]').classes()).not.toContain(
      'workspace-navigation__link--active',
    )

    const menuButton = wrapper.get('button[aria-label="Mở menu điều hướng"]')
    await menuButton.trigger('click')
    expect(wrapper.get('.workspace-sidebar').classes()).toContain('workspace-sidebar--open')
    expect(document.body.classList.contains('workspace-menu-open')).toBe(true)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(wrapper.get('.workspace-sidebar').classes()).not.toContain('workspace-sidebar--open')
    expect(document.activeElement).toBe(menuButton.element)

    wrapper.unmount()
    expect(document.body.classList.contains('workspace-menu-open')).toBe(false)
  })
})
