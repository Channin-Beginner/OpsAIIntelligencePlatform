import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  clearStoredToken,
  getStoredToken,
  setStoredToken,
  UserRole,
  type AuthUser,
  type LoginRequest,
} from '@opsai/shared'
import { login as loginApi } from '@/api/auth'

const USER_KEY = 'opsai_admin_user'

function loadUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

function saveUser(user: AuthUser | null) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(loadUser())
  const token = ref<string | null>(getStoredToken())

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === UserRole.ADMIN)

  async function login(credentials: LoginRequest) {
    const data = await loginApi(credentials)
    if (data.role !== UserRole.ADMIN) {
      throw new Error('仅管理员账号可登录管理台')
    }
    const authUser: AuthUser = {
      userId: data.user_id,
      username: data.username,
      displayName: data.display_name,
      role: data.role,
      token: data.access_token,
    }
    setStoredToken(data.access_token)
    saveUser(authUser)
    token.value = data.access_token
    user.value = authUser
  }

  function logout() {
    clearStoredToken()
    saveUser(null)
    token.value = null
    user.value = null
  }

  return { user, token, isLoggedIn, isAdmin, login, logout }
})
