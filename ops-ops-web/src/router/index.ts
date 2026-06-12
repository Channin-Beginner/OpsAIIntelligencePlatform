import { createRouter, createWebHistory } from 'vue-router'
import { getStoredToken } from '@opsai/shared'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/OpsLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '运维大屏' },
        },
        {
          path: 'alerts',
          name: 'alerts',
          component: () => import('@/views/AlertsView.vue'),
          meta: { title: '告警列表' },
        },
        {
          path: 'incidents',
          name: 'incidents',
          component: () => import('@/views/IncidentsView.vue'),
          meta: { title: '故障列表' },
        },
        {
          path: 'incidents/:id',
          name: 'incident-detail',
          component: () => import('@/views/IncidentDetailView.vue'),
          meta: { title: '故障详情' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!getStoredToken()) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
