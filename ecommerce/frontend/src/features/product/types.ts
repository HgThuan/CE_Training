import type { PaginationMeta } from '@/shared/types/api'

export type ProductStatus =
  'draft' | 'pending_review' | 'approved' | 'rejected' | 'hidden' | 'suspended'

export interface Category {
  id: string
  parent_id: string | null
  name: string
  slug: string
  image_url: string | null
  sort_order: number
  is_active: boolean
  children: Category[]
  created_at: string
  updated_at: string
}

export interface CategoryOption {
  id: string
  name: string
  depth: number
}

export interface Brand {
  id: string
  name: string
  slug: string
  logo_url: string | null
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategorySummary {
  id: string
  name: string
  slug: string
}

export interface BrandSummary {
  id: string
  name: string
  slug: string
  logo_url: string | null
}

export interface ProductMedia {
  id: string
  variant_id: string | null
  media_type: 'image' | 'video'
  file_url: string
  thumbnail_url: string | null
  alt_text: string | null
  sort_order: number
  is_primary: boolean
  created_at: string
}

export interface AttributeValue {
  id: string
  value: string
  display_value: string | null
  color_code: string | null
  sort_order: number
}

export interface ProductAttribute {
  id: string
  name: string
  code: string
  display_type: 'text' | 'color' | 'image'
  values: AttributeValue[]
}

export interface SellerAttribute extends ProductAttribute {
  sort_order: number
  scope: 'global' | 'shop'
}

export interface VariantAttribute {
  attribute_id: string
  attribute_name: string
  attribute_value_id: string
  value: string
  display_value: string | null
  color_code: string | null
}

export interface ProductVariant {
  id: string
  sku: string
  name: string | null
  original_price: string
  sale_price: string
  weight_grams: number | null
  attributes: VariantAttribute[]
}

export interface SellerProductVariant extends ProductVariant {
  barcode: string | null
  cost_price: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ShopSummary {
  id: number
  name: string
  slug: string
  logo_url: string | null
  average_rating: string
}

export interface PublicProductListItem {
  id: string
  name: string
  slug: string
  thumbnail: string | null
  min_price: string | null
  max_price: string | null
  rating_average: string
  rating_count: number
  sold_count: number
  shop_name: string
  shop_slug: string
}

export interface PublicProductDetail {
  id: string
  name: string
  slug: string
  short_description: string | null
  description: string | null
  category: CategorySummary
  brand: BrandSummary | null
  shop: ShopSummary
  media: ProductMedia[]
  variants: ProductVariant[]
  attributes: ProductAttribute[]
  min_price: string | null
  max_price: string | null
  rating_average: string
  rating_count: number
  sold_count: number
  created_at: string
  updated_at: string
}

export interface ProductListFilters {
  category_id?: string
  brand_id?: string
  min_price?: string
  max_price?: string
  search?: string
  sort?: ProductSort
  page?: number
  page_size?: number
}

export type ProductSort =
  | 'created_at'
  | '-created_at'
  | 'price'
  | '-price'
  | 'sold_count'
  | '-sold_count'
  | 'rating'
  | '-rating'

export interface ProductCatalogState {
  categories: Category[]
  brands: Brand[]
  meta: PaginationMeta
}

export interface SellerProductListItem {
  id: string
  name: string
  slug: string
  status: ProductStatus
  thumbnail: string | null
  min_price: string | null
  max_price: string | null
  created_at: string
}

export interface SellerProductDetail {
  id: string
  name: string
  slug: string
  short_description: string | null
  description: string | null
  status: ProductStatus
  rejection_reason: string | null
  category: CategorySummary
  brand: BrandSummary | null
  media: ProductMedia[]
  variants: SellerProductVariant[]
  attributes: ProductAttribute[]
  min_price: string | null
  max_price: string | null
  rating_average: string
  rating_count: number
  sold_count: number
  created_at: string
  updated_at: string
}

export interface SellerProductPayload {
  name: string
  category_id: string
  brand_id?: string | null
  short_description?: string | null
  description?: string | null
}

export interface SellerProductFilters {
  status?: ProductStatus
  category_id?: string
  search?: string
  sort?: ProductSort
  page?: number
  page_size?: number
}

export interface VariantUpdatePayload {
  sku?: string
  barcode?: string | null
  original_price?: string
  sale_price?: string
  cost_price?: string | null
  weight_grams?: number
  is_active?: boolean
}

export interface AdminProductListItem {
  id: string
  name: string
  slug: string
  status: ProductStatus
  rejection_reason: string | null
  thumbnail: string | null
  min_price: string | null
  max_price: string | null
  category: CategorySummary
  shop_name: string
  seller_id: number
  seller_email: string
  seller_name: string
  created_at: string
}

export interface CategoryPayload {
  name: string
  slug?: string
  parent?: string | null
  image_url?: string | null
  sort_order?: number
  is_active?: boolean
}

export interface BrandPayload {
  name: string
  slug?: string
  logo_url?: string | null
  description?: string | null
  is_active?: boolean
}
