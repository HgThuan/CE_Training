import { computed, reactive } from 'vue'

import type { ProductAttribute, ProductVariant } from '../types'

export type VariantSelection = Record<string, string>

export function variantMatchesSelection(
  variant: ProductVariant,
  selection: VariantSelection,
  ignoredAttributeId?: string,
): boolean {
  return Object.entries(selection).every(([attributeId, valueId]) => {
    if (!valueId || attributeId === ignoredAttributeId) return true
    return variant.attributes.some(
      (attribute) =>
        attribute.attribute_id === attributeId && attribute.attribute_value_id === valueId,
    )
  })
}

export function findSelectedVariant(
  variants: ProductVariant[],
  attributes: ProductAttribute[],
  selection: VariantSelection,
): ProductVariant | null {
  if (!attributes.length || attributes.some((attribute) => !selection[attribute.id])) return null
  return (
    variants.find(
      (variant) =>
        variant.attributes.length === attributes.length &&
        variantMatchesSelection(variant, selection),
    ) ?? null
  )
}

export function isVariantValueAvailable(
  variants: ProductVariant[],
  selection: VariantSelection,
  attributeId: string,
  valueId: string,
): boolean {
  return variants.some(
    (variant) =>
      variant.stock_quantity > 0 &&
      variant.attributes.some(
        (attribute) =>
          attribute.attribute_id === attributeId && attribute.attribute_value_id === valueId,
      ) &&
      variantMatchesSelection(variant, selection, attributeId),
  )
}

export function useVariantSelection(
  attributes: () => ProductAttribute[],
  variants: () => ProductVariant[],
) {
  const selection = reactive<VariantSelection>({})
  const selectedVariant = computed(() => findSelectedVariant(variants(), attributes(), selection))
  const isComplete = computed(
    () =>
      attributes().length > 0 &&
      attributes().every((attribute) => Boolean(selection[attribute.id])),
  )

  function select(attributeId: string, valueId: string): void {
    if (selection[attributeId] === valueId) {
      delete selection[attributeId]
      return
    }
    selection[attributeId] = valueId
    for (const attribute of attributes()) {
      const selectedValue = selection[attribute.id]
      if (
        selectedValue &&
        !isVariantValueAvailable(variants(), selection, attribute.id, selectedValue)
      ) {
        delete selection[attribute.id]
      }
    }
  }

  function isAvailable(attributeId: string, valueId: string): boolean {
    return isVariantValueAvailable(variants(), selection, attributeId, valueId)
  }

  return { selection, selectedVariant, isComplete, select, isAvailable }
}
