import type { Category } from '@/features/product/types'

import { buildCategoryTree, containsCategory, siblingReorderItems } from './category-tree'

function category(id: string, parentId: string | null, sortOrder: number): Category {
  return {
    id,
    parent_id: parentId,
    name: id,
    slug: id,
    image_url: null,
    sort_order: sortOrder,
    is_active: true,
    children: [],
    created_at: '',
    updated_at: '',
  }
}

describe('admin category tree', () => {
  it('builds and sorts a multi-level tree from the paginated flat response', () => {
    const tree = buildCategoryTree([
      category('child-2', 'root', 2),
      category('root', null, 0),
      category('child-1', 'root', 1),
    ])
    expect(tree).toHaveLength(1)
    expect(tree[0]?.children.map((item) => item.id)).toEqual(['child-1', 'child-2'])
  })

  it('detects descendants to prevent a drag-and-drop cycle', () => {
    const tree = buildCategoryTree([category('root', null, 0), category('child', 'root', 0)])
    expect(containsCategory(tree[0]!, 'child')).toBe(true)
    expect(containsCategory(tree[0]!, 'other')).toBe(false)
  })

  it('normalizes sibling sort order for the reorder API', () => {
    const siblings = [category('a', null, 5), category('b', null, 10)]
    expect(siblingReorderItems(siblings).map((item) => item.sort_order)).toEqual([0, 1])
  })
})
