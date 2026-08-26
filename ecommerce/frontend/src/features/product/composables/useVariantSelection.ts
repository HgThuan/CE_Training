import { computed, reactive, watch } from 'vue'

import type { ProductAttribute, ProductVariant } from '../types'

export type VariantSelection = Record<string, string>

export function selectableVariantAttributes(
  attributes: ProductAttribute[],
  variants: ProductVariant[],
): ProductAttribute[] {
  if (!attributes.length || !variants.length) return []

  const linkedAttributeIds = new Set(
    variants.flatMap((variant) => variant.attributes.map((attribute) => attribute.attribute_id)),
  )
  if (!linkedAttributeIds.size) return []

  const selectable = attributes.filter((attribute) => linkedAttributeIds.has(attribute.id))
  const selectableIds = new Set(selectable.map((attribute) => attribute.id))
  if (selectableIds.size !== linkedAttributeIds.size) return []

  const variantsHaveCompleteLinks = variants.every((variant) => {
    const variantAttributeIds = new Set(
      variant.attributes.map((attribute) => attribute.attribute_id),
    )
    return (
      variantAttributeIds.size === selectableIds.size &&
      [...selectableIds].every((attributeId) => variantAttributeIds.has(attributeId))
    )
  })

  return variantsHaveCompleteLinks ? selectable : []
}

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
      variant.attributes.some(
        (attribute) =>
          attribute.attribute_id === attributeId && attribute.attribute_value_id === valueId,
      ) && variantMatchesSelection(variant, selection, attributeId),
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

  watch([attributes, variants], () => {
    for (const attributeId of Object.keys(selection)) delete selection[attributeId]
  })

  return { selection, selectedVariant, isComplete, select, isAvailable }
}
