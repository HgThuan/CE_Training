import type { Banner } from './types'

export function bannersForPosition(banners: Banner[], position: Banner['position']): Banner[] {
  return banners
    .filter((banner) => banner.position === position)
    .sort((left, right) => left.sort_order - right.sort_order || left.id.localeCompare(right.id))
}

export function reorderBanners(
  banners: Banner[],
  sourceId: string,
  targetId: string,
): Banner[] | null {
  const source = banners.find((banner) => banner.id === sourceId)
  const target = banners.find((banner) => banner.id === targetId)
  if (!source || !target || source.position !== target.position || source.id === target.id) {
    return null
  }

  const siblings = bannersForPosition(banners, source.position)
  const sourceIndex = siblings.findIndex((banner) => banner.id === source.id)
  const targetIndex = siblings.findIndex((banner) => banner.id === target.id)
  const [moved] = siblings.splice(sourceIndex, 1)
  if (!moved) return null
  siblings.splice(targetIndex, 0, moved)
  return siblings
}

export function moveBanner(
  banners: Banner[],
  bannerId: string,
  direction: -1 | 1,
): Banner[] | null {
  const banner = banners.find((item) => item.id === bannerId)
  if (!banner) return null
  const siblings = bannersForPosition(banners, banner.position)
  const index = siblings.findIndex((item) => item.id === bannerId)
  const target = siblings[index + direction]
  return target ? reorderBanners(banners, bannerId, target.id) : null
}
