const acceptedAvatarTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])
const maxAvatarBytes = 5 * 1024 * 1024

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Không thể đọc tệp ảnh đã chọn'))
    image.src = url
  })
}

export async function cropAvatarToSquare(file: File, size = 512): Promise<Blob> {
  if (!acceptedAvatarTypes.has(file.type)) {
    throw new Error('Chỉ chấp nhận ảnh JPEG, PNG hoặc WebP')
  }
  if (file.size > maxAvatarBytes) {
    throw new Error('Ảnh đại diện không được vượt quá 5 MB')
  }

  const objectUrl = URL.createObjectURL(file)
  try {
    const image = await loadImage(objectUrl)
    const sourceSize = Math.min(image.naturalWidth, image.naturalHeight)
    const sourceX = (image.naturalWidth - sourceSize) / 2
    const sourceY = (image.naturalHeight - sourceSize) / 2
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Trình duyệt không hỗ trợ xử lý ảnh')
    context.drawImage(image, sourceX, sourceY, sourceSize, sourceSize, 0, 0, size, size)

    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('Không thể cắt ảnh đại diện'))),
        'image/jpeg',
        0.88,
      )
    })
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}
