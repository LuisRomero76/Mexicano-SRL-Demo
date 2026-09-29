import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ACCESO } from '@/lib/roles'
import { useAuthStore, type Rol } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    roles?: Rol[]
  }
}

const publico: RouteRecordRaw = {
  path: '/',
  component: () => import('@/layouts/PublicLayout.vue'),
  children: [
    { path: '', name: 'inicio', component: () => import('@/pages/public/HomePage.vue') },
    {
      path: 'pasajes',
      name: 'resultados',
      component: () => import('@/pages/public/ResultsPage.vue'),
      meta: { title: 'Salidas disponibles' },
    },
    {
      path: 'pasajes/:salidaId/asientos',
      name: 'asientos',
      component: () => import('@/pages/public/SeatsPage.vue'),
      meta: { title: 'Elige tus asientos' },
    },
    {
      path: 'compra/pasajeros',
      name: 'pasajeros',
      component: () => import('@/pages/public/PassengersPage.vue'),
      meta: { title: 'Datos de los pasajeros' },
    },
    {
      path: 'compra/pago/:codigo',
      name: 'pago',
      component: () => import('@/pages/public/PaymentPage.vue'),
      meta: { title: 'Pago' },
    },
    {
      path: 'compra/confirmacion/:codigo',
      name: 'confirmacion',
      component: () => import('@/pages/public/ConfirmationPage.vue'),
      meta: { title: 'Compra confirmada' },
    },
    {
      path: 'mi-reserva',
      name: 'mi-reserva',
      component: () => import('@/pages/public/MyBookingPage.vue'),
      meta: { title: 'Mi reserva' },
    },
    {
      path: 'rastreo/:guia?',
      name: 'rastreo',
      component: () => import('@/pages/public/TrackingPage.vue'),
      meta: { title: 'Rastrear envío' },
    },
    {
      path: 'carga',
      name: 'carga',
      component: () => import('@/pages/public/CargoPage.vue'),
      meta: { title: 'Carga y encomiendas' },
    },
    {
      path: 'carga/puerta-a-puerta',
      name: 'puerta-a-puerta',
      component: () => import('@/pages/public/DoorToDoorPage.vue'),
      meta: { title: 'Puerta a puerta' },
    },
    { path: 'rutas', name: 'rutas', component: () => import('@/pages/public/RoutesPage.vue'), meta: { title: 'Rutas e itinerarios' } },
    { path: 'buses', name: 'buses', component: () => import('@/pages/public/BusesPage.vue'), meta: { title: 'Nuestros buses' } },
    {
      path: 'oficinas',
      name: 'oficinas',
      component: () => import('@/pages/public/OfficesPage.vue'),
      meta: { title: 'Boleterías y bodegas' },
    },
    { path: 'ayuda', name: 'ayuda', component: () => import('@/pages/public/HelpPage.vue'), meta: { title: 'Centro de ayuda' } },
    {
      path: 'terminos',
      name: 'terminos',
      component: () => import('@/pages/public/ContentPage.vue'),
      props: { slug: 'terminos' },
      meta: { title: 'Términos y condiciones' },
    },
    {
      path: 'p/:slug',
      name: 'pagina',
      component: () => import('@/pages/public/ContentPage.vue'),
      props: true,
      meta: { title: 'Información' },
    },
    {
      path: ':pathMatch(.*)*',
      name: 'no-encontrado',
      component: () => import('@/pages/public/NotFoundPage.vue'),
      meta: { title: 'Página no encontrada' },
    },
  ],
}

const panel: RouteRecordRaw[] = [
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('@/pages/admin/LoginPage.vue'),
    meta: { title: 'Iniciar sesión' },
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'admin-tablero', component: () => import('@/pages/admin/DashboardPage.vue'), meta: { title: 'Tablero' } },
      {
        path: 'salidas',
        name: 'admin-salidas',
        component: () => import('@/pages/admin/DeparturesPage.vue'),
        meta: { title: 'Salidas', roles: ACCESO.salidas },
      },
      {
        path: 'salidas/:id',
        name: 'admin-salida',
        component: () => import('@/pages/admin/DepartureDetailPage.vue'),
        meta: { title: 'Detalle de salida', roles: ACCESO.salidas },
      },
      {
        path: 'boleteria',
        name: 'admin-boleteria',
        component: () => import('@/pages/admin/TicketOfficePage.vue'),
        meta: { title: 'Boletería', roles: ACCESO.boleteria },
      },
      {
        path: 'abordaje',
        name: 'admin-abordaje',
        component: () => import('@/pages/admin/BoardingPage.vue'),
        meta: { title: 'Abordaje', roles: ACCESO.abordaje },
      },
      {
        path: 'ventas',
        name: 'admin-ventas',
        component: () => import('@/pages/admin/SalesPage.vue'),
        meta: { title: 'Ventas', roles: ACCESO.ventas },
      },
      {
        path: 'reembolsos',
        name: 'admin-reembolsos',
        component: () => import('@/pages/admin/RefundsPage.vue'),
        meta: { title: 'Reembolsos', roles: ACCESO.reembolsos },
      },
      {
        path: 'encomiendas',
        name: 'admin-encomiendas',
        component: () => import('@/pages/admin/ParcelsPage.vue'),
        meta: { title: 'Encomiendas', roles: ACCESO.encomiendas },
      },
      {
        path: 'encomiendas/nueva',
        name: 'admin-encomienda-nueva',
        component: () => import('@/pages/admin/ParcelNewPage.vue'),
        meta: { title: 'Registrar encomienda', roles: ACCESO.encomiendasRegistrar },
      },
      {
        path: 'encomiendas/:guia',
        name: 'admin-encomienda',
        component: () => import('@/pages/admin/ParcelDetailPage.vue'),
        meta: { title: 'Encomienda', roles: ACCESO.encomiendas },
      },
      {
        path: 'puerta-a-puerta',
        name: 'admin-puerta',
        component: () => import('@/pages/admin/DoorToDoorBoardPage.vue'),
        meta: { title: 'Puerta a puerta', roles: ACCESO.puerta },
      },
      {
        path: 'catalogos/:seccion?',
        name: 'admin-catalogos',
        component: () => import('@/pages/admin/CatalogsPage.vue'),
        meta: { title: 'Catálogos', roles: ACCESO.catalogos },
      },
      {
        path: 'personal',
        name: 'admin-personal',
        component: () => import('@/pages/admin/StaffPage.vue'),
        meta: { title: 'Personal', roles: ACCESO.personal },
      },
      {
        path: 'clientes',
        name: 'admin-clientes',
        component: () => import('@/pages/admin/CustomersPage.vue'),
        meta: { title: 'Clientes', roles: ACCESO.clientes },
      },
      {
        path: 'reportes',
        name: 'admin-reportes',
        component: () => import('@/pages/admin/ReportsPage.vue'),
        meta: { title: 'Reportes', roles: ACCESO.reportes },
      },
      {
        path: 'auditoria',
        name: 'admin-auditoria',
        component: () => import('@/pages/admin/AuditPage.vue'),
        meta: { title: 'Auditoría', roles: ACCESO.auditoria },
      },
      {
        path: 'sin-permiso',
        name: 'admin-sin-permiso',
        component: () => import('@/pages/admin/ForbiddenPage.vue'),
        meta: { title: 'Sin permiso' },
      },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [...panel, publico],
  scrollBehavior(to, _from, guardado) {
    if (guardado) return guardado
    if (to.hash) return { el: to.hash, behavior: 'smooth', top: 88 }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.name === 'admin-login') {
    await auth.cargarSesion()
    if (auth.estado === 'autenticado') return { name: 'admin-tablero' }
    return true
  }
  if (!to.matched.some((r) => r.meta.requiresAuth)) return true
  await auth.cargarSesion()
  if (auth.estado !== 'autenticado') {
    return { name: 'admin-login', query: { siguiente: to.fullPath } }
  }
  if (to.meta.roles && !auth.puede(to.meta.roles)) return { name: 'admin-sin-permiso' }
  return true
})

router.afterEach((to) => {
  const base = to.path.startsWith('/admin') ? 'Panel El Mexicano' : 'El Mexicano'
  document.title = to.meta.title ? `${to.meta.title} · ${base}` : `${base} · Pasajes de bus, carga y encomiendas`
})
