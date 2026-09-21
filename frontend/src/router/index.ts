import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import OverviewView from '../views/OverviewView.vue'
import BloggerDetailView from '../views/BloggerDetailView.vue'
import ImportView from '../views/ImportView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: AppLayout, children: [{ path: '', component: OverviewView }] },
    { path: '/bloggers/:id', component: AppLayout, children: [{ path: '', component: BloggerDetailView }] },
    { path: '/import', component: AppLayout, children: [{ path: '', component: ImportView }] },
    { path: '/history', component: AppLayout, children: [{ path: '', component: HistoryView }] },
    { path: '/settings', component: AppLayout, children: [{ path: '', component: SettingsView }] },
  ],
})

export default router
