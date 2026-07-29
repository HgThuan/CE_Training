import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import { productApi } from '../api'
import type { ProductQuestion } from '../types'
import QASection from './QASection.vue'

vi.mock('../api', () => ({
  productApi: {
    createQuestion: vi.fn(),
    listQuestions: vi.fn(),
  },
}))

const question: ProductQuestion = {
  id: 'question-1',
  product_id: 'product-1',
  customer: {
    id: 10,
    full_name: 'Nguyễn Minh',
    avatar_url: '',
  },
  content: 'Sản phẩm được bảo hành bao lâu?',
  status: 'visible',
  answer: {
    id: 'answer-1',
    seller: {
      id: 20,
      full_name: 'Future Shop',
      avatar_url: '',
    },
    content: 'Sản phẩm được bảo hành chính hãng 12 tháng.',
    created_at: '2026-07-28T08:00:00Z',
    updated_at: '2026-07-28T08:00:00Z',
  },
  created_at: '2026-07-27T08:00:00Z',
  updated_at: '2026-07-28T08:00:00Z',
}

const customer: AuthenticatedUser = {
  id: 10,
  email: 'customer@example.com',
  role: 'customer',
  is_active: true,
  is_email_verified: true,
  must_change_password: false,
  avatar_url: '',
  full_name: 'Nguyễn Minh',
  phone: '',
  date_of_birth: null,
  gender: '',
  profile: null,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

function questionListResponse(
  data: ProductQuestion[] = [question],
  page = 1,
  totalPages = 1,
): Awaited<ReturnType<typeof productApi.listQuestions>> {
  return {
    data: {
      success: true,
      message: 'Lấy hỏi đáp thành công',
      data,
      meta: {
        page,
        page_size: 10,
        total_items: data.length,
        total_pages: totalPages,
      },
    },
  } as Awaited<ReturnType<typeof productApi.listQuestions>>
}

async function mountSection(user: AuthenticatedUser | null = null) {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/products/:slug', component },
      { path: '/auth/login', component },
    ],
  })
  await router.push('/products/dien-thoai#description')
  await router.isReady()

  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.user = user
  authStore.accessToken = user ? 'access-token' : null

  const wrapper = mount(QASection, {
    props: { productId: 'product-1' },
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return { router, wrapper }
}

describe('QASection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(productApi.listQuestions).mockResolvedValue(questionListResponse())
    vi.mocked(productApi.createQuestion).mockResolvedValue({
      data: {
        success: true,
        message: 'Đã gửi câu hỏi',
        data: question,
      },
    } as Awaited<ReturnType<typeof productApi.createQuestion>>)
  })

  it('renders public questions and sends guests back to the Q&A tab after login', async () => {
    const { wrapper } = await mountSection()

    expect(wrapper.text()).toContain('Sản phẩm được bảo hành bao lâu?')
    expect(wrapper.text()).toContain('bảo hành chính hãng 12 tháng')
    expect(wrapper.text()).not.toContain('customer@example.com')
    expect(wrapper.get('a').attributes('href')).toContain('redirect=/products/dien-thoai%23qa')
    wrapper.unmount()
  })

  it('lets a customer submit a trimmed question and refreshes the first page', async () => {
    const { wrapper } = await mountSection(customer)

    await wrapper.get('textarea').setValue('  Sản phẩm có chống nước không?  ')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(productApi.createQuestion).toHaveBeenCalledWith('product-1', {
      content: 'Sản phẩm có chống nước không?',
    })
    expect(productApi.listQuestions).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Đã gửi câu hỏi')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
    wrapper.unmount()
  })

  it('shows an API error and retries the current page', async () => {
    vi.mocked(productApi.listQuestions)
      .mockRejectedValueOnce(new Error('Mất kết nối'))
      .mockResolvedValueOnce(questionListResponse())

    const { wrapper } = await mountSection()
    expect(wrapper.text()).toContain('Mất kết nối')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(productApi.listQuestions).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Sản phẩm được bảo hành bao lâu?')
    wrapper.unmount()
  })

  it('loads the requested Q&A page', async () => {
    vi.mocked(productApi.listQuestions)
      .mockResolvedValueOnce(questionListResponse([question], 1, 2))
      .mockResolvedValueOnce(questionListResponse([question], 2, 2))

    const { wrapper } = await mountSection()
    await wrapper.get('button[aria-label="Trang hỏi đáp sau"]').trigger('click')
    await flushPromises()

    expect(productApi.listQuestions).toHaveBeenLastCalledWith('product-1', {
      page: 2,
      page_size: 10,
    })
    expect(wrapper.text()).toContain('Trang 2 / 2')
    wrapper.unmount()
  })
})
