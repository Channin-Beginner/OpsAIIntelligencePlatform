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
      component: () => import('@/layouts/AdminLayout.vue'),
      children: [
        { path: '', redirect: '/admin/users' },
        {
          path: 'admin/users',
          name: 'admin-users',
          component: () => import('@/views/UsersView.vue'),
          meta: { title: '用户管理' },
        },
        {
          path: 'admin/integration',
          name: 'admin-integration',
          component: () => import('@/views/IntegrationView.vue'),
          meta: { title: '接入配置' },
        },
        {
          path: 'admin/kb',
          name: 'admin-kb',
          component: () => import('@/views/KbArticlesView.vue'),
          meta: { title: '知识库' },
        },
        {
          path: 'admin/runbooks',
          name: 'admin-runbooks',
          component: () => import('@/views/RunbooksView.vue'),
          meta: { title: 'Runbook 管理' },
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
