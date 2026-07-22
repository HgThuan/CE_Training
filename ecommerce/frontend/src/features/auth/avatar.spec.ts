import { describe, expect, it } from 'vitest'

import { cropAvatarToSquare } from './avatar'

describe('cropAvatarToSquare', () => {
  it('rejects unsupported file types before decoding the image', async () => {
    const file = new File(['not-an-image'], 'avatar.svg', { type: 'image/svg+xml' })

    await expect(cropAvatarToSquare(file)).rejects.toThrow('JPEG, PNG hoặc WebP')
  })

  it('rejects avatars larger than 5 MB before decoding the image', async () => {
    const file = new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'avatar.jpg', {
      type: 'image/jpeg',
    })

    await expect(cropAvatarToSquare(file)).rejects.toThrow('không được vượt quá 5 MB')
  })
})
