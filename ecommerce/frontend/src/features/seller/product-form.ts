import type {
  AttributeValue,
  SellerAttribute,
  SellerProductVariant,
} from '@/features/product/types'

export interface VariantDraft {
  key: string
  variantId?: string
  label: string
  attributeValueIds: string[]
  sku: string
  barcode: string
  originalPrice: string
  salePrice: string
  costPrice: string
  weightGrams: string
  isActive: boolean
}

export interface PendingMedia {
  id: string
  file: File
  mediaType: 'image' | 'video'
  previewUrl: string
}

function cartesianProduct<T>(groups: T[][]): T[][] {
  if (!groups.length) return []
  return groups.reduce<T[][]>(
    (combinations, group) =>
      combinations.flatMap((combination) => group.map((value) => [...combination, value])),
    [[]],
  )
}

export function variantKey(valueIds: string[]): string {
  return [...valueIds].sort().join('|')
}

export function generateVariantDrafts(
  attributes: SellerAttribute[],
  selectedValueIds: Record<string, string[]>,
  currentDrafts: VariantDraft[] = [],
): VariantDraft[] {
  const selectedGroups = attributes
    .map((attribute) => ({
      attribute,
      values: attribute.values.filter((value) =>
        selectedValueIds[attribute.id]?.includes(value.id),
      ),
    }))
    .filter((group) => group.values.length)

  if (!selectedGroups.length) return []
  const previousByKey = new Map(currentDrafts.map((draft) => [draft.key, draft]))
  return cartesianProduct(selectedGroups.map((group) => group.values)).map((combination) => {
    const key = variantKey(combination.map((value) => value.id))
    const previous = previousByKey.get(key)
    return {
      key,
      label: combination.map((value) => value.display_value || value.value).join(' / '),
      attributeValueIds: combination.map((value) => value.id),
      sku: previous?.sku ?? '',
      barcode: previous?.barcode ?? '',
      originalPrice: previous?.originalPrice ?? '',
      salePrice: previous?.salePrice ?? '',
      costPrice: previous?.costPrice ?? '',
      weightGrams: previous?.weightGrams ?? '',
      isActive: previous?.isActive ?? true,
    }
  })
}

export function variantToDraft(variant: SellerProductVariant): VariantDraft {
  const valueIds = variant.attributes.map((attribute) => attribute.attribute_value_id)
  return {
    key: variantKey(valueIds),
    variantId: variant.id,
    label:
      variant.name ||
      variant.attributes.map((attribute) => attribute.display_value || attribute.value).join(' / '),
    attributeValueIds: valueIds,
    sku: variant.sku,
    barcode: variant.barcode ?? '',
    originalPrice: variant.original_price,
    salePrice: variant.sale_price,
    costPrice: variant.cost_price ?? '',
    weightGrams: variant.weight_grams?.toString() ?? '',
    isActive: variant.is_active,
  }
}

export function validateVariantDrafts(
  drafts: VariantDraft[],
  requireVariant = true,
): string | null {
  if (!drafts.length) {
    return requireVariant ? 'Vui lòng chọn thuộc tính để tạo ít nhất một SKU.' : null
  }
  const skus = new Set<string>()
  const barcodes = new Set<string>()
  for (const draft of drafts) {
    const originalPrice = Number(draft.originalPrice)
    const salePrice = Number(draft.salePrice)
    if (!draft.sku.trim()) return `SKU của biến thể “${draft.label}” không được để trống.`
    if (skus.has(draft.sku.trim())) return `SKU “${draft.sku.trim()}” đang bị trùng.`
    skus.add(draft.sku.trim())
    if (draft.barcode.trim()) {
      if (barcodes.has(draft.barcode.trim())) {
        return `Barcode “${draft.barcode.trim()}” đang bị trùng.`
      }
      barcodes.add(draft.barcode.trim())
    }
    if (!Number.isFinite(originalPrice) || originalPrice < 0) {
      return `Giá gốc của biến thể “${draft.label}” không hợp lệ.`
    }
    if (!Number.isFinite(salePrice) || salePrice < 0) {
      return `Giá bán của biến thể “${draft.label}” không hợp lệ.`
    }
    if (originalPrice !== 0 && salePrice > originalPrice) {
      return `Giá bán của biến thể “${draft.label}” không được cao hơn giá gốc.`
    }
  }
  return null
}

export async function detectMediaType(file: File): Promise<'image' | 'video' | null> {
  const header = new Uint8Array(await file.slice(0, 32).arrayBuffer())
  const isJpeg = header[0] === 0xff && header[1] === 0xd8 && header[2] === 0xff
  const isPng = header[0] === 0x89 && header[1] === 0x50 && header[2] === 0x4e && header[3] === 0x47
  const isWebp =
    String.fromCharCode(...header.slice(0, 4)) === 'RIFF' &&
    String.fromCharCode(...header.slice(8, 12)) === 'WEBP'
  const isMp4 = String.fromCharCode(...header.slice(4, 8)) === 'ftyp'
  const isWebm =
    header[0] === 0x1a && header[1] === 0x45 && header[2] === 0xdf && header[3] === 0xa3
  if (isJpeg || isPng || isWebp) return 'image'
  if (isMp4 || isWebm) return 'video'
  return null
}

export async function validateMediaFile(
  file: File,
): Promise<{ mediaType: 'image' | 'video' } | { error: string }> {
  const mediaType = await detectMediaType(file)
  if (!mediaType) return { error: `${file.name}: chỉ hỗ trợ JPEG, PNG, WebP, MP4 hoặc WebM.` }
  const maxBytes = (mediaType === 'image' ? 10 : 100) * 1024 * 1024
  if (file.size <= 0 || file.size > maxBytes) {
    return {
      error: `${file.name}: ${mediaType === 'image' ? 'ảnh' : 'video'} vượt giới hạn ${
        mediaType === 'image' ? 10 : 100
      } MB.`,
    }
  }
  return { mediaType }
}

export function attributeValueById(
  attributes: SellerAttribute[],
  valueId: string,
): AttributeValue | undefined {
  return attributes.flatMap((attribute) => attribute.values).find((value) => value.id === valueId)
}
