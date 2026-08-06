import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, beforeEach, vi } from 'vitest'

import { searchApi } from '../api'
import type { SearchSuggestion } from '../types'
import SearchBar from './SearchBar.vue'

vi.mock('../api', () => ({
  searchApi: {
    search: vi.fn(),
    suggestions: vi.fn(),
  },
}))

function response(data: SearchSuggestion[]) {
  return {
    data: {
      success: true,
      message: 'ok',
      data,
    },
  } as Awaited<ReturnType<typeof searchApi.suggestions>>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

async function mountSearchBar() {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component },
      { path: '/search', component },
    ],
  })
  await router.push('/')
  await router.isReady()
  return {
    router,
    wrapper: mount(SearchBar, { global: { plugins: [router] } }),
  }
}

describe('SearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('debounces autocomplete and ignores a stale response', async () => {
    const first = deferred<Awaited<ReturnType<typeof searchApi.suggestions>>>()
    const second = deferred<Awaited<ReturnType<typeof searchApi.suggestions>>>()
    vi.mocked(searchApi.suggestions)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
    const { wrapper } = await mountSearchBar()
    const input = wrapper.get('input[role="combobox"]')

    await input.setValue('dien')
    await vi.advanceTimersByTimeAsync(250)
    await input.setValue('laptop')
    await vi.advanceTimersByTimeAsync(250)

    second.resolve(response([{ id: '2', text: 'Laptop gaming' }]))
    await flushPromises()
    expect(wrapper.text()).toContain('Laptop gaming')

    first.resolve(response([{ id: '1', text: 'Điện thoại' }]))
    await flushPromises()
    expect(wrapper.text()).not.toContain('Điện thoại')
    wrapper.unmount()
  })

  it('supports arrow navigation and submits the active suggestion', async () => {
    vi.mocked(searchApi.suggestions).mockResolvedValue(
      response([
        { id: '1', text: 'Điện thoại' },
        { id: '2', text: 'Điện thoại chống nước' },
      ]),
    )
    const { router, wrapper } = await mountSearchBar()
    const input = wrapper.get('input[role="combobox"]')

    await input.setValue('dien')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/search')
    expect(router.currentRoute.value.query.q).toBe('Điện thoại')
    wrapper.unmount()
  })
})
