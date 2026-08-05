<script setup lang="ts">
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { Chart, registerables } from 'chart.js'
import type { ChartPoint } from '../types'

Chart.register(...registerables)

const props = defineProps<{ points: ChartPoint[] }>()
const canvasRef = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

function renderChart() {
  if (!canvasRef.value) return
  if (chartInstance) {
    chartInstance.destroy()
  }

  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  const gradient = ctx.createLinearGradient(0, 0, 0, 300)
  gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)') // Indigo 500
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0)')

  const labels = props.points.map(p => {
    const d = new Date(p.date)
    return isNaN(d.getTime()) ? p.date : d.toLocaleDateString('vi-VN', { month: 'numeric', day: 'numeric' })
  })
  
  const data = props.points.map(p => Number(p.revenue))

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Doanh thu',
          data,
          borderColor: '#6366f1',
          backgroundColor: gradient,
          borderWidth: 3,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#6366f1',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: true,
          tension: 0.4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleFont: { size: 13, family: 'Inter, sans-serif' },
          bodyFont: { size: 14, weight: 'bold', family: 'Inter, sans-serif' },
          padding: 12,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            label: (context) => {
              return Number(context.raw).toLocaleString('vi-VN') + ' ₫'
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { family: 'Inter, sans-serif' } }
        },
        y: {
          border: { display: false },
          grid: { color: '#f1f5f9' },
          beginAtZero: true,
          ticks: {
            color: '#64748b',
            font: { family: 'Inter, sans-serif' },
            callback: (value) => {
              const num = Number(value)
              if (num >= 1000000) return (num / 1000000).toLocaleString('vi-VN') + 'Tr'
              if (num >= 1000) return (num / 1000).toLocaleString('vi-VN') + 'K'
              return num.toLocaleString('vi-VN')
            }
          }
        }
      },
      interaction: {
        mode: 'index',
        intersect: false,
      }
    }
  })
}

onMounted(renderChart)
watch(() => props.points, renderChart, { deep: true })
onBeforeUnmount(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>

<template>
  <div class="relative h-72 w-full" aria-label="Biểu đồ doanh thu">
    <canvas ref="canvasRef"></canvas>
    <div v-if="!points.length" class="absolute inset-0 flex items-center justify-center bg-white/80">
      <p class="text-sm font-medium text-slate-500">Chưa có dữ liệu doanh thu trong kỳ.</p>
    </div>
  </div>
</template>
