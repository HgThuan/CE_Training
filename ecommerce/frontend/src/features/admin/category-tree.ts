import type { Category } from '@/features/product/types'

export function buildCategoryTree(categories: Category[]): Category[] {
  const byId = new Map<string, Category>()
  for (const category of categories) {
    byId.set(category.id, { ...category, children: [] })
  }
  const roots: Category[] = []
  for (const category of byId.values()) {
    const parent = category.parent_id ? byId.get(category.parent_id) : undefined
    if (parent) parent.children.push(category)
    else roots.push(category)
  }
  const sort = (items: Category[]): void => {
    items.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name, 'vi'))
    items.forEach((item) => sort(item.children))
  }
  sort(roots)
  return roots
}

export function containsCategory(category: Category, candidateId: string): boolean {
  return (
    category.id === candidateId ||
    category.children.some((child) => containsCategory(child, candidateId))
  )
}

export function findCategory(categories: Category[], categoryId: string): Category | null {
  for (const category of categories) {
    if (category.id === categoryId) return category
    const nested = findCategory(category.children, categoryId)
    if (nested) return nested
  }
  return null
}

export function siblingReorderItems(
  siblings: Category[],
): { id: string; parent_id: string | null; sort_order: number }[] {
  return siblings.map((category, index) => ({
    id: category.id,
    parent_id: category.parent_id,
    sort_order: index,
  }))
}
