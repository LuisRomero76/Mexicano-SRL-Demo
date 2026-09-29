<script setup lang="ts">
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import VChart from 'vue-echarts'

use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

defineProps<{ option: EChartsOption; height?: string; label: string }>()
</script>

<template>
  <div role="img" :aria-label="label" :style="{ height: height ?? '260px' }">
    <VChart :option="option" autoresize class="size-full" />
  </div>
</template>
