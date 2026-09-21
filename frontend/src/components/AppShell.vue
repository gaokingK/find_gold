<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getActiveNavPath,
  getPageRouteMetadata,
  navigationItems,
} from '../utils/presentation'

const route = useRoute()
const router = useRouter()

const activePath = computed(() => getActiveNavPath(route.path))
const routeMetadata = computed(() => getPageRouteMetadata(route.path))
</script>

<template>
  <div class="app-shell">
    <a class="skip-link" href="#main-content">跳转到主要内容</a>
    <aside class="sidebar" aria-label="Fund Lens 应用导航">
      <div class="brand-block">
        <div class="brand-mark" role="img" aria-label="Fund Lens，博主追踪台">F</div>
        <div>
          <strong>Fund Lens</strong>
          <span>博主追踪台</span>
        </div>
      </div>
      <div class="sidebar-section-label">工作台</div>
      <nav class="main-nav" aria-label="主导航">
        <button
          v-for="item in navigationItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: activePath === item.path }"
          :aria-current="activePath === item.path ? 'page' : undefined"
          :aria-label="item.ariaLabel ?? item.label"
          :title="item.label"
          type="button"
          @click="router.push(item.path)"
        >
          <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footer" role="status" aria-label="演示运行状态">
        <span class="status-dot" aria-hidden="true"></span>
        <span>本地 Demo 模式</span>
      </div>
    </aside>
    <div class="main-frame">
      <header class="topbar">
        <div>
          <span class="eyebrow">{{ routeMetadata.pathLabel }}</span>
          <h1 id="page-title">{{ routeMetadata.title }}</h1>
        </div>
        <div class="topbar-note" role="status" aria-live="polite" aria-atomic="true">
          <span class="pulse-dot" aria-hidden="true"></span>
          <span>数据仅供演示</span>
        </div>
      </header>
      <main id="main-content" class="content-area" aria-labelledby="page-title" tabindex="-1"><slot /></main>
    </div>
  </div>
</template>
