<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { ElMessage } from 'element-plus'
import type { DashboardOverview } from '@opsai/shared'
import { getDashboardOverview } from '@/api/dashboard'

const loading = ref(false)
const data = ref<DashboardOverview | null>(null)

const alertChartRef = ref<HTMLDivElement | null>(null)
const funnelChartRef = ref<HTMLDivElement | null>(null)
const serviceChartRef = ref<HTMLDivElement | null>(null)
const mttrChartRef = ref<HTMLDivElement | null>(null)
const rootCauseChartRef = ref<HTMLDivElement | null>(null)

let charts: ECharts[] = []
let timer: number | undefined

const kpi = computed(() => data.value?.core_kpi)

function disposeCharts() {
  charts.forEach((c) => c.dispose())
  charts = []
}

function mountChart(el: HTMLDivElement | null, option: echarts.EChartsOption) {
  if (!el) return
  const chart = echarts.init(el, undefined, { renderer: 'canvas' })
  chart.setOption(option)
  charts.push(chart)
}

function renderCharts() {
  if (!data.value) return
  disposeCharts()

  const d = data.value
  const hours = d.alert_curve_24h.map((p) => p.hour.slice(11, 16))
  mountChart(alertChartRef.value, {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: ['原始', '去重'], textStyle: { color: '#cbd5e1' } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: hours, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#334155' } } },
    series: [
      { name: '原始', type: 'line', smooth: true, data: d.alert_curve_24h.map((p) => p.raw_count), color: '#f59e0b' },
      { name: '去重', type: 'line', smooth: true, data: d.alert_curve_24h.map((p) => p.deduped_count), color: '#38bdf8' },
    ],
  })

  mountChart(funnelChartRef.value, {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'funnel',
        left: '10%',
        width: '80%',
        label: { color: '#e2e8f0' },
        data: d.incident_funnel.map((f) => ({ name: f.status, value: f.count })),
      },
    ],
  })

  mountChart(serviceChartRef.value, {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#cbd5e1' } },
    grid: { left: 48, right: 16, top: 36, bottom: 48 },
    xAxis: {
      type: 'category',
      data: d.service_health_top.map((s) => s.service),
      axisLabel: { color: '#94a3b8', rotate: 20 },
    },
    yAxis: [
      { type: 'value', name: '错误率%', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#334155' } } },
      { type: 'value', name: 'P95s', axisLabel: { color: '#94a3b8' }, splitLine: { show: false } },
    ],
    series: [
      { name: '错误率%', type: 'bar', data: d.service_health_top.map((s) => s.error_rate), color: '#ef4444' },
      { name: 'P95s', type: 'line', yAxisIndex: 1, data: d.service_health_top.map((s) => s.p95_seconds), color: '#a78bfa' },
    ],
  })

  mountChart(mttrChartRef.value, {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 24, bottom: 28 },
    xAxis: {
      type: 'category',
      data: d.mttr_trend_30d.map((p) => p.date.slice(5)),
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: { type: 'value', name: '分钟', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#334155' } } },
    series: [
      {
        name: 'MTTR',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        data: d.mttr_trend_30d.map((p) => p.mttr_avg_minutes ?? 0),
        color: '#22c55e',
      },
    ],
  })

  mountChart(rootCauseChartRef.value, {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 120, right: 16, top: 8, bottom: 8 },
    xAxis: { type: 'value', axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#334155' } } },
    yAxis: {
      type: 'category',
      data: d.top_root_causes.map((r) => r.root_cause.slice(0, 24)),
      axisLabel: { color: '#94a3b8', width: 110, overflow: 'truncate' },
    },
    series: [{ type: 'bar', data: d.top_root_causes.map((r) => r.count), color: '#6366f1' }],
  })
}

async function fetchData() {
  loading.value = true
  try {
    data.value = await getDashboardOverview()
    renderCharts()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载大屏失败')
  } finally {
    loading.value = false
  }
}

function handleResize() {
  charts.forEach((c) => c.resize())
}

watch(data, () => renderCharts())

onMounted(() => {
  fetchData()
  timer = window.setInterval(fetchData, 60000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  disposeCharts()
})
</script>

<template>
  <div v-loading="loading" class="dashboard">
    <header class="dash-header">
      <div>
        <h1>OpsAI 运维大屏</h1>
        <p>Data Flywheel · MTTR · Agent 质量 · 统一告警</p>
      </div>
      <el-button type="primary" plain @click="fetchData">刷新</el-button>
    </header>

    <section class="kpi-row">
      <div class="kpi-card">
        <span class="kpi-label">平均 MTTR（分钟）</span>
        <strong class="kpi-value">{{ kpi?.mttr_avg_minutes ?? '—' }}</strong>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">开放 Incident</span>
        <strong class="kpi-value accent-warn">{{ kpi?.open_incidents ?? 0 }}</strong>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">今日告警</span>
        <strong class="kpi-value accent-info">{{ kpi?.today_alerts ?? 0 }}</strong>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">RCA 采纳率</span>
        <strong class="kpi-value">
          {{ data ? `${(data.rca_quality.rca_accept_feedback_rate * 100).toFixed(1)}%` : '—' }}
        </strong>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Runbook 成功率</span>
        <strong class="kpi-value">
          {{ data ? `${(data.runbook_success.success_rate * 100).toFixed(1)}%` : '—' }}
        </strong>
      </div>
    </section>

    <section class="grid">
      <div class="panel span-2">
        <h3>24h 告警曲线（原始 vs 去重）</h3>
        <div ref="alertChartRef" class="chart" />
      </div>
      <div class="panel">
        <h3>Incident 状态漏斗</h3>
        <div ref="funnelChartRef" class="chart" />
      </div>
      <div class="panel span-2">
        <h3>服务健康 TOP（错误率 / P95）</h3>
        <div ref="serviceChartRef" class="chart" />
      </div>
      <div class="panel">
        <h3>RCA / Runbook 质量</h3>
        <ul class="stat-list" v-if="data">
          <li>RCA 推荐 Runbook：{{ data.rca_quality.recommended_count }}</li>
          <li>已采纳执行：{{ data.rca_quality.adopted_count }}</li>
          <li>Runbook 执行：{{ data.runbook_success.total_executions }}</li>
          <li>成功：{{ data.runbook_success.successful_executions }}</li>
        </ul>
      </div>
      <div class="panel span-2">
        <h3>近 30 日 MTTR 趋势</h3>
        <div ref="mttrChartRef" class="chart" />
      </div>
      <div class="panel span-2">
        <h3>Top 根因分类</h3>
        <div ref="rootCauseChartRef" class="chart tall" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: calc(100vh - 96px);
  color: #e2e8f0;
  background: radial-gradient(ellipse at top, #1e293b 0%, #0f172a 55%);
  margin: -20px;
  padding: 20px 24px 32px;
}

.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.dash-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.dash-header p {
  margin: 6px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  background: rgba(30, 41, 59, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 10px;
  padding: 14px 16px;
}

.kpi-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
}

.kpi-value {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  line-height: 1;
}

.accent-warn {
  color: #fbbf24;
}

.accent-info {
  color: #38bdf8;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.panel {
  background: rgba(15, 23, 42, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 10px;
  padding: 12px 14px 8px;
}

.panel.span-2 {
  grid-column: span 2;
}

.panel h3 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #cbd5e1;
}

.chart {
  height: 220px;
}

.chart.tall {
  height: 260px;
}

.stat-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  line-height: 2;
  color: #cbd5e1;
  font-size: 14px;
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .panel.span-2 {
    grid-column: span 1;
  }
}
</style>
