<script setup lang="ts">
import { ArrowUpRightIcon, BoltIcon, StarIcon } from '@heroicons/vue/24/outline'
import { computed, ref } from 'vue'

import type { PublicProductListItem } from '@/features/product/types'
import { formatVnd } from '@/shared/lib/formatters'

const props = defineProps<{ product: PublicProductListItem }>()
const imageFailed = ref(false)
const hasPriceRange = computed(
  () =>
    Boolean(props.product.min_price && props.product.max_price) &&
    Number(props.product.max_price) > Number(props.product.min_price),
)
const hasDiscount = computed(
  () =>
    Boolean(props.product.is_flash_sale && props.product.regular_min_price) &&
    Number(props.product.regular_min_price) > Number(props.product.min_price),
)
</script>

<template>
  <article class="chat-product-card" data-test="product-card">
    <RouterLink
      :to="{
        name: 'product-detail',
        params: { slug: product.slug },
        query: { shop: product.shop_slug },
      }"
      class="chat-product-card__link"
      :aria-label="`Xem ${product.name}`"
    >
      <div class="chat-product-card__media">
        <img
          v-if="product.thumbnail && !imageFailed"
          :src="product.thumbnail"
          :alt="product.name"
          loading="lazy"
          decoding="async"
          @error="imageFailed = true"
        />
        <div
          v-else
          class="chat-product-card__fallback"
          role="img"
          :aria-label="`Chưa có ảnh cho ${product.name}`"
        >
          <span>M</span>
          <small>Ảnh đang cập nhật</small>
        </div>
        <span v-if="product.is_flash_sale" class="chat-product-card__sale">
          <BoltIcon aria-hidden="true" />
          Flash Sale
        </span>
      </div>

      <div class="chat-product-card__content">
        <p class="chat-product-card__shop">{{ product.shop_name }}</p>
        <h4>{{ product.name }}</h4>
        <div v-if="product.rating_count" class="chat-product-card__rating">
          <StarIcon aria-hidden="true" />
          <strong>{{ Number(product.rating_average).toFixed(1) }}</strong>
          <span>({{ product.rating_count }})</span>
        </div>
        <div class="chat-product-card__footer">
          <div>
            <p class="chat-product-card__price">
              {{
                hasPriceRange ? `Từ ${formatVnd(product.min_price)}` : formatVnd(product.min_price)
              }}
            </p>
            <p v-if="hasDiscount" class="chat-product-card__regular-price">
              {{ formatVnd(product.regular_min_price) }}
            </p>
          </div>
          <span class="chat-product-card__action" aria-hidden="true">
            <span>Xem chi tiết</span>
            <ArrowUpRightIcon />
          </span>
        </div>
      </div>
    </RouterLink>
  </article>
</template>

<style scoped>
.chat-product-card {
  overflow: hidden;
  border-radius: 0.875rem;
  background: #fffdf8;
  box-shadow: 0 8px 24px rgb(23 59 53 / 9%);
}

.chat-product-card__link {
  display: grid;
  min-height: 8rem;
  grid-template-columns: 7rem minmax(0, 1fr);
  color: #0b2a25;
  text-decoration: none;
}

.chat-product-card__link:focus-visible {
  outline: 3px solid rgb(232 93 63 / 45%);
  outline-offset: -3px;
}

.chat-product-card__media {
  position: relative;
  min-height: 8rem;
  overflow: hidden;
  background: #ece8de;
}

.chat-product-card__media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 360ms cubic-bezier(0.16, 1, 0.3, 1);
}

.chat-product-card__link:hover .chat-product-card__media img {
  transform: scale(1.035);
}

.chat-product-card__fallback {
  display: grid;
  height: 100%;
  min-height: 8rem;
  place-content: center;
  gap: 0.35rem;
  background: #e8eee9;
  color: #526762;
  text-align: center;
}

.chat-product-card__fallback span {
  font-size: 1.25rem;
  font-weight: 900;
}

.chat-product-card__fallback small {
  max-width: 5rem;
  font-size: 0.6875rem;
  font-weight: 700;
  line-height: 1.25;
}

.chat-product-card__sale {
  position: absolute;
  right: 0.4rem;
  bottom: 0.4rem;
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  border-radius: 0.45rem;
  background: #e85d3f;
  padding: 0.25rem 0.4rem;
  color: white;
  font-size: 0.625rem;
  font-weight: 850;
  line-height: 1;
}

.chat-product-card__sale svg {
  width: 0.7rem;
  height: 0.7rem;
}

.chat-product-card__content {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 0.75rem;
}

.chat-product-card__shop {
  overflow: hidden;
  color: #526762;
  font-size: 0.6875rem;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-product-card h4 {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 0.2rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.875rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  line-height: 1.35;
}

.chat-product-card__rating {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  margin-top: 0.35rem;
  color: #526762;
  font-size: 0.6875rem;
}

.chat-product-card__rating svg {
  width: 0.85rem;
  height: 0.85rem;
  fill: #f2c14e;
  color: #f2c14e;
}

.chat-product-card__rating strong {
  color: #173b35;
}

.chat-product-card__footer {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.45rem;
}

.chat-product-card__price {
  color: #e85d3f;
  font-size: 0.9375rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.chat-product-card__regular-price {
  color: #71827e;
  font-size: 0.6875rem;
  text-decoration: line-through;
}

.chat-product-card__action {
  display: inline-flex;
  min-height: 2rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  border-radius: 0.6rem;
  padding-inline: 0.55rem;
  background: #e8eee9;
  color: #173b35;
  font-size: 0.6875rem;
  font-weight: 800;
  transition:
    color 160ms ease-out,
    background-color 160ms ease-out;
}

.chat-product-card__action svg {
  width: 1rem;
  height: 1rem;
}

.chat-product-card__link:hover .chat-product-card__action {
  background: #173b35;
  color: white;
}

@media (max-width: 359px) {
  .chat-product-card__link {
    grid-template-columns: 5.75rem minmax(0, 1fr);
  }

  .chat-product-card__action span {
    display: none;
  }

  .chat-product-card__action {
    width: 2rem;
    padding: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chat-product-card__media img,
  .chat-product-card__action {
    transition: none;
  }
}
</style>
