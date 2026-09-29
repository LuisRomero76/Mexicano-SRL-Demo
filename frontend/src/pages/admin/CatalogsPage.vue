<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import {
  BadgeDollarSign,
  Building2,
  Bus,
  CalendarClock,
  CalendarX2,
  CircleHelp,
  Clock,
  FileText,
  Handshake,
  Route,
  SlidersHorizontal,
  Truck,
  Weight,
} from '@lucide/vue'
import { computed, ref, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, unwrap } from '@/api/client'
import { pedir, type Fila, type Pagina } from '@/api/crud'
import { useCiudades, useTiposAsiento } from '@/api/queries'
import CrudSection, { type CampoCrud, type ColumnaCrud } from '@/components/admin/CrudSection.vue'
import OfficeHoursDialog from '@/components/admin/OfficeHoursDialog.vue'
import PagesEditor from '@/components/admin/PagesEditor.vue'
import ParametersSection from '@/components/admin/ParametersSection.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import { bsExacto, duracion, fechaCorta, telefono } from '@/lib/format'
import { DIAS, TIPO_ENVIO, TIPO_OFICINA } from '@/lib/labels'
import type { Rol } from '@/stores/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const esSupervisor = computed(() => auth.puede(['supervisor']))

interface Seccion {
  key: string
  label: string
  icono: Component
  roles: Rol[]
  grupo: string
}
const SECCIONES: Seccion[] = [
  { key: 'oficinas', label: 'Oficinas', icono: Building2, roles: ['supervisor'], grupo: 'Red' },
  { key: 'rutas', label: 'Rutas', icono: Route, roles: ['supervisor'], grupo: 'Red' },
  { key: 'horarios', label: 'Horarios de salida', icono: Clock, roles: ['supervisor'], grupo: 'Red' },
  { key: 'feriados', label: 'Feriados', icono: CalendarX2, roles: ['supervisor'], grupo: 'Red' },
  { key: 'buses', label: 'Buses', icono: Bus, roles: ['supervisor'], grupo: 'Flota' },
  { key: 'vehiculos', label: 'Vehículos de carga', icono: Truck, roles: ['supervisor'], grupo: 'Flota' },
  { key: 'tarifas-pasaje', label: 'Tarifas de pasaje', icono: BadgeDollarSign, roles: ['supervisor'], grupo: 'Precios' },
  { key: 'tarifas-carga', label: 'Tarifas de carga', icono: Weight, roles: ['supervisor'], grupo: 'Precios' },
  { key: 'cuentas', label: 'Cuentas corporativas', icono: Handshake, roles: ['supervisor'], grupo: 'Precios' },
  { key: 'faqs', label: 'Preguntas frecuentes', icono: CircleHelp, roles: ['supervisor', 'soporte'], grupo: 'Contenido' },
  { key: 'paginas', label: 'Páginas del sitio', icono: FileText, roles: ['supervisor', 'soporte'], grupo: 'Contenido' },
  { key: 'parametros', label: 'Parámetros', icono: SlidersHorizontal, roles: ['admin'], grupo: 'Sistema' },
]
const disponibles = computed(() => SECCIONES.filter((s) => auth.puede(s.roles)))
const grupos = computed(() => [...new Set(disponibles.value.map((s) => s.grupo))])
const seccion = computed(() => {
  const k = route.params.seccion
  return disponibles.value.find((s) => s.key === k) ?? disponibles.value[0]
})
function ir(key: string | number | null | undefined): void {
  void router.replace({ name: 'admin-catalogos', params: { seccion: String(key) } })
}

// --- Datos de apoyo para selects y columnas ---
const { data: ciudades } = useCiudades()
const { data: tiposAsiento } = useTiposAsiento()
const rutas = useQuery({
  queryKey: ['crud', '/api/v1/admin/rutas', 'todas'],
  queryFn: () => pedir<Pagina<Fila>>('GET', '/api/v1/admin/rutas', { params: { query: { limit: 100 } } }),
  enabled: esSupervisor,
})
const oficinas = useQuery({
  queryKey: ['crud', '/api/v1/admin/oficinas', 'todas'],
  queryFn: () => pedir<Pagina<Fila>>('GET', '/api/v1/admin/oficinas', { params: { query: { limit: 100 } } }),
  enabled: esSupervisor,
})
const categoriasFaq = useQuery({ queryKey: ['faqs'], queryFn: () => unwrap(api.GET('/api/v1/faqs')) })

const ciudad = (id: number | null) => ciudades.value?.find((c) => c.id === id)?.nombre ?? (id ? `#${id}` : '—')
const ruta = (id: number) => {
  const r = rutas.data.value?.items.find((x) => x.id === id)
  return r ? `${ciudad(r.origen_ciudad_id)} → ${ciudad(r.destino_ciudad_id)}` : `#${id}`
}
const oficina = (id: number | null) => oficinas.data.value?.items.find((o) => o.id === id)?.nombre ?? (id ? `#${id}` : '—')
const asiento = (id: number) => tiposAsiento.value?.find((t) => t.id === id)?.nombre ?? `#${id}`

const opCiudades = computed(() => (ciudades.value ?? []).map((c) => ({ value: c.id, label: c.nombre })))
const opRutas = computed(() => (rutas.data.value?.items ?? []).map((r) => ({ value: r.id as number, label: `${r.codigo} · ${ruta(r.id)}` })))
const opOficinas = computed(() => (oficinas.data.value?.items ?? []).map((o) => ({ value: o.id as number, label: o.nombre as string })))
const opAsientos = computed(() => (tiposAsiento.value ?? []).map((t) => ({ value: t.id, label: t.nombre })))
const opCategorias = computed(() => (categoriasFaq.data.value ?? []).filter((c) => c.id).map((c) => ({ value: c.id!, label: c.nombre })))
const opTipoOficina = Object.entries(TIPO_OFICINA).map(([value, label]) => ({ value, label }))
const opTipoEnvio = Object.entries(TIPO_ENVIO).map(([value, label]) => ({ value, label }))
const opEstadoBus = [
  { value: 'operativo', label: 'Operativo' },
  { value: 'mantenimiento', label: 'En mantenimiento' },
  { value: 'fuera_de_servicio', label: 'Fuera de servicio' },
]
const opTipoVehiculo = [
  { value: 'furgon', label: 'Furgón' },
  { value: 'camion', label: 'Camión' },
  { value: 'furgoneta_reparto', label: 'Furgoneta de reparto' },
]
const categoria = (id: number) => categoriasFaq.data.value?.find((c) => c.id === id)?.nombre ?? `#${id}`
const vigencia = (f: Fila) => `${fechaCorta(f.vigente_desde)}${f.vigente_hasta ? ` – ${fechaCorta(f.vigente_hasta)}` : ' en adelante'}`

// Filtros por sección
const filtroRuta = ref<number | null>(null)

// --- Configuración de cada catálogo ---
interface Config {
  titulo: string
  descripcion?: string
  ruta: string
  columnas: ColumnaCrud[]
  campos: CampoCrud[]
  clave?: string
  paginado?: boolean
  puedeCrear?: boolean
  puedeEditar?: boolean
  puedeEliminar?: boolean
  nombreItem: string
  buscarEn?: string[]
}
const configs = computed<Record<string, Config>>(() => ({
  oficinas: {
    titulo: 'Oficinas',
    descripcion: 'Boleterías y bodegas de carga. Los cambios se ven al instante en el sitio.',
    ruta: '/api/v1/admin/oficinas',
    nombreItem: 'oficina',
    buscarEn: ['nombre', 'codigo', 'direccion'],
    columnas: [
      { key: 'codigo', label: 'Código', mono: true },
      { key: 'nombre', label: 'Nombre' },
      { key: 'ciudad_id', label: 'Ciudad', valor: (f) => ciudad(f.ciudad_id) },
      { key: 'tipo', label: 'Tipo', hideSm: true, valor: (f) => TIPO_OFICINA[f.tipo] },
      { key: 'telefono_e164', label: 'Teléfono', hideSm: true, valor: (f) => telefono(f.telefono_e164) },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'ciudad_id', label: 'Ciudad', tipo: 'select', opciones: opCiudades.value, requerido: true, soloCrear: true },
      { key: 'codigo', label: 'Código', requerido: true, soloCrear: true, ayuda: 'Ej.: SRE-BOD' },
      { key: 'nombre', label: 'Nombre', requerido: true },
      { key: 'tipo', label: 'Tipo', tipo: 'select', opciones: opTipoOficina, requerido: true },
      { key: 'direccion', label: 'Dirección', requerido: true, ancho: 'full' },
      { key: 'referencia', label: 'Referencia', ancho: 'full' },
      { key: 'telefono_e164', label: 'Teléfono', ayuda: 'Formato +591…' },
      { key: 'whatsapp_e164', label: 'WhatsApp', ayuda: 'Formato +591…' },
      { key: 'url_mapa', label: 'Enlace de Google Maps', ancho: 'full' },
      { key: 'es_principal', label: 'Oficina principal de la ciudad', tipo: 'checkbox' },
      { key: 'activo', label: 'Activa', tipo: 'checkbox', soloEditar: true },
    ],
  },
  rutas: {
    titulo: 'Rutas',
    descripcion: 'Las rutas se crean con la base de datos; aquí se ajustan distancia, duración y el cargo por exceso de equipaje.',
    ruta: '/api/v1/admin/rutas',
    nombreItem: 'ruta',
    puedeCrear: false,
    columnas: [
      { key: 'codigo', label: 'Código', mono: true },
      { key: 'trayecto', label: 'Trayecto', valor: (f) => `${ciudad(f.origen_ciudad_id)} → ${ciudad(f.destino_ciudad_id)}` },
      { key: 'distancia_km', label: 'Distancia', align: 'right', valor: (f) => `${f.distancia_km} km` },
      { key: 'duracion_estimada_min', label: 'Duración', hideSm: true, valor: (f) => duracion(f.duracion_estimada_min) },
      { key: 'cargo_exceso_equipaje_kg_bs', label: 'Exceso / kg', hideSm: true, align: 'right', valor: (f) => bsExacto(f.cargo_exceso_equipaje_kg_bs) },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'distancia_km', label: 'Distancia (km)', tipo: 'number', requerido: true },
      { key: 'duracion_estimada_min', label: 'Duración (minutos)', tipo: 'number', requerido: true },
      { key: 'cargo_exceso_equipaje_kg_bs', label: 'Cargo por kg de exceso (Bs)', tipo: 'decimal' },
      { key: 'activo', label: 'Activa', tipo: 'checkbox' },
      { key: 'descripcion', label: 'Descripción', tipo: 'textarea' },
    ],
  },
  horarios: {
    titulo: 'Horarios de salida',
    descripcion: 'Plantillas con las que se generan las salidas de cada día.',
    ruta: '/api/v1/admin/plantillas-horario',
    nombreItem: 'horario',
    columnas: [
      { key: 'ruta_id', label: 'Ruta', valor: (f) => ruta(f.ruta_id) },
      { key: 'hora_salida', label: 'Hora', valor: (f) => String(f.hora_salida).slice(0, 5) },
      { key: 'dias_semana', label: 'Días', valor: (f) => (f.dias_semana.length === 7 ? 'Todos los días' : f.dias_semana.map((d: number) => DIAS[d - 1].slice(0, 3)).join(' ')) },
      { key: 'oficina_salida_id', label: 'Sale de', hideSm: true, valor: (f) => oficina(f.oficina_salida_id) },
      { key: 'vigencia', label: 'Vigencia', hideSm: true, valor: vigencia },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'ruta_id', label: 'Ruta', tipo: 'select', opciones: opRutas.value, requerido: true, soloCrear: true, ancho: 'full' },
      { key: 'hora_salida', label: 'Hora de salida', tipo: 'time', requerido: true, soloCrear: true },
      { key: 'oficina_salida_id', label: 'Oficina de salida', tipo: 'select', opciones: opOficinas.value },
      { key: 'dias_semana', label: 'Días de la semana', tipo: 'dias', requerido: true },
      { key: 'vigente_desde', label: 'Vigente desde', tipo: 'date', requerido: true, soloCrear: true },
      { key: 'vigente_hasta', label: 'Vigente hasta', tipo: 'date' },
      { key: 'activo', label: 'Activo', tipo: 'checkbox', soloEditar: true },
    ],
  },
  feriados: {
    titulo: 'Feriados',
    descripcion: 'El puerta a puerta no opera en feriados; también se muestran en el calendario de compra.',
    ruta: '/api/v1/admin/feriados',
    nombreItem: 'feriado',
    paginado: false,
    puedeEditar: false,
    puedeEliminar: true,
    columnas: [
      { key: 'fecha', label: 'Fecha', valor: (f) => fechaCorta(f.fecha) },
      { key: 'nombre', label: 'Feriado' },
      { key: 'departamento', label: 'Alcance', valor: (f) => f.departamento ?? 'Nacional' },
    ],
    campos: [
      { key: 'fecha', label: 'Fecha', tipo: 'date', requerido: true },
      { key: 'nombre', label: 'Nombre', requerido: true },
      { key: 'departamento', label: 'Departamento', ayuda: 'Vacío si es nacional', ancho: 'full' },
    ],
  },
  buses: {
    titulo: 'Buses',
    descripcion: 'Al registrar un bus se crea su mapa de 48 asientos en dos pisos.',
    ruta: '/api/v1/admin/buses',
    nombreItem: 'bus',
    paginado: false,
    buscarEn: ['numero_interno', 'placa', 'marca'],
    columnas: [
      { key: 'numero_interno', label: 'Interno', mono: true },
      { key: 'placa', label: 'Placa', mono: true },
      { key: 'modelo', label: 'Marca y modelo', hideSm: true, valor: (f) => [f.marca, f.modelo, f.anio].filter(Boolean).join(' ') },
      { key: 'capacidad_total', label: 'Asientos', align: 'right' },
      { key: 'estado', label: 'Operación', valor: (f) => opEstadoBus.find((e) => e.value === f.estado)?.label },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'numero_interno', label: 'Número interno', requerido: true, soloCrear: true },
      { key: 'placa', label: 'Placa', requerido: true, soloCrear: true, ayuda: 'Ej.: 4521KDB' },
      { key: 'marca', label: 'Marca' },
      { key: 'modelo', label: 'Modelo' },
      { key: 'anio', label: 'Año', tipo: 'number' },
      { key: 'estado', label: 'Operación', tipo: 'select', opciones: opEstadoBus, valorInicial: 'operativo' },
      { key: 'activo', label: 'Activo', tipo: 'checkbox', soloEditar: true },
    ],
  },
  vehiculos: {
    titulo: 'Vehículos de carga',
    descripcion: 'Furgones con GPS para carga de más de 30 kg y furgonetas de reparto.',
    ruta: '/api/v1/admin/vehiculos-carga',
    nombreItem: 'vehículo',
    columnas: [
      { key: 'placa', label: 'Placa', mono: true },
      { key: 'tipo', label: 'Tipo', valor: (f) => opTipoVehiculo.find((t) => t.value === f.tipo)?.label },
      { key: 'capacidad_kg', label: 'Capacidad', align: 'right', valor: (f) => `${f.capacidad_kg.toLocaleString('es-BO')} kg` },
      { key: 'ciudad_base_id', label: 'Base', hideSm: true, valor: (f) => ciudad(f.ciudad_base_id) },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'placa', label: 'Placa', requerido: true, soloCrear: true },
      { key: 'tipo', label: 'Tipo', tipo: 'select', opciones: opTipoVehiculo, requerido: true, soloCrear: true },
      { key: 'capacidad_kg', label: 'Capacidad (kg)', tipo: 'number', requerido: true },
      { key: 'ciudad_base_id', label: 'Ciudad base', tipo: 'select', opciones: opCiudades.value },
      { key: 'activo', label: 'Activo', tipo: 'checkbox', soloEditar: true },
    ],
  },
  'tarifas-pasaje': {
    titulo: 'Tarifas de pasaje',
    descripcion: 'Precio por ruta y clase. El precio máximo referencial es el tope aprobado por la ATT.',
    ruta: '/api/v1/admin/tarifas-pasaje',
    nombreItem: 'tarifa',
    columnas: [
      { key: 'ruta_id', label: 'Ruta', valor: (f) => ruta(f.ruta_id) },
      { key: 'tipo_asiento_id', label: 'Clase', valor: (f) => asiento(f.tipo_asiento_id) },
      { key: 'precio_bs', label: 'Precio', align: 'right', valor: (f) => bsExacto(f.precio_bs) },
      { key: 'precio_maximo_referencial_bs', label: 'Tope ATT', align: 'right', hideSm: true, valor: (f) => bsExacto(f.precio_maximo_referencial_bs) },
      { key: 'vigencia', label: 'Vigencia', hideSm: true, valor: vigencia },
    ],
    campos: [
      { key: 'ruta_id', label: 'Ruta', tipo: 'select', opciones: opRutas.value, requerido: true, soloCrear: true, ancho: 'full' },
      { key: 'tipo_asiento_id', label: 'Clase', tipo: 'select', opciones: opAsientos.value, requerido: true, soloCrear: true },
      { key: 'vigente_desde', label: 'Vigente desde', tipo: 'date', requerido: true, soloCrear: true },
      { key: 'precio_bs', label: 'Precio (Bs)', tipo: 'decimal', requerido: true },
      { key: 'precio_maximo_referencial_bs', label: 'Precio máximo referencial (Bs)', tipo: 'decimal', requerido: true },
      { key: 'vigente_hasta', label: 'Vigente hasta', tipo: 'date' },
    ],
  },
  'tarifas-carga': {
    titulo: 'Tarifas de carga',
    descripcion: 'Precio base por tramo y tipo de envío, más el costo por kilo adicional.',
    ruta: '/api/v1/admin/tarifas-carga',
    nombreItem: 'tarifa',
    columnas: [
      { key: 'tramo', label: 'Tramo', valor: (f) => `${ciudad(f.origen_ciudad_id)} → ${ciudad(f.destino_ciudad_id)}` },
      { key: 'tipo_envio', label: 'Tipo', valor: (f) => TIPO_ENVIO[f.tipo_envio] },
      { key: 'peso', label: 'Peso', hideSm: true, valor: (f) => `${f.peso_min_kg}${f.peso_max_kg ? `–${f.peso_max_kg}` : '+'} kg` },
      { key: 'precio_base_bs', label: 'Base', align: 'right', valor: (f) => bsExacto(f.precio_base_bs) },
      { key: 'precio_kg_adicional_bs', label: 'Kg adicional', align: 'right', hideSm: true, valor: (f) => bsExacto(f.precio_kg_adicional_bs) },
      { key: 'recargo_puerta_a_puerta_bs', label: 'Puerta a puerta', align: 'right', hideSm: true, valor: (f) => bsExacto(f.recargo_puerta_a_puerta_bs) },
    ],
    campos: [
      { key: 'origen_ciudad_id', label: 'Origen', tipo: 'select', opciones: opCiudades.value, requerido: true, soloCrear: true },
      { key: 'destino_ciudad_id', label: 'Destino', tipo: 'select', opciones: opCiudades.value, requerido: true, soloCrear: true },
      { key: 'tipo_envio', label: 'Tipo de envío', tipo: 'select', opciones: opTipoEnvio, requerido: true, soloCrear: true },
      { key: 'peso_min_kg', label: 'Peso mínimo (kg)', tipo: 'decimal', requerido: true, soloCrear: true },
      { key: 'peso_max_kg', label: 'Peso máximo (kg)', tipo: 'decimal' },
      { key: 'precio_base_bs', label: 'Precio base (Bs)', tipo: 'decimal', requerido: true },
      { key: 'precio_kg_adicional_bs', label: 'Por kg adicional (Bs)', tipo: 'decimal' },
      { key: 'recargo_puerta_a_puerta_bs', label: 'Recargo puerta a puerta (Bs)', tipo: 'decimal' },
      { key: 'vigente_desde', label: 'Vigente desde', tipo: 'date', requerido: true, soloCrear: true },
      { key: 'vigente_hasta', label: 'Vigente hasta', tipo: 'date' },
    ],
  },
  cuentas: {
    titulo: 'Cuentas corporativas',
    descripcion: 'Empresas que envían carga a crédito.',
    ruta: '/api/v1/admin/cuentas-corporativas',
    nombreItem: 'cuenta',
    buscarEn: ['razon_social', 'codigo', 'nit'],
    columnas: [
      { key: 'codigo', label: 'Código', mono: true },
      { key: 'razon_social', label: 'Razón social' },
      { key: 'nit', label: 'NIT', hideSm: true },
      { key: 'saldo', label: 'Saldo / límite', align: 'right', valor: (f) => `${bsExacto(f.saldo_pendiente_bs)} / ${bsExacto(f.limite_credito_bs)}` },
      { key: 'dias_credito', label: 'Plazo', hideSm: true, valor: (f) => `${f.dias_credito} días` },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'codigo', label: 'Código', requerido: true, soloCrear: true },
      { key: 'nit', label: 'NIT', requerido: true, soloCrear: true },
      { key: 'razon_social', label: 'Razón social', requerido: true, ancho: 'full' },
      { key: 'contacto_nombre', label: 'Contacto' },
      { key: 'contacto_telefono_e164', label: 'Teléfono del contacto' },
      { key: 'contacto_email', label: 'Correo del contacto', ancho: 'full' },
      { key: 'limite_credito_bs', label: 'Límite de crédito (Bs)', tipo: 'decimal' },
      { key: 'dias_credito', label: 'Días de crédito', tipo: 'number' },
      { key: 'saldo_pendiente_bs', label: 'Saldo pendiente (Bs)', tipo: 'decimal', soloEditar: true, ayuda: 'Ajústalo al registrar un pago' },
      { key: 'activo', label: 'Activa', tipo: 'checkbox', soloEditar: true },
    ],
  },
  faqs: {
    titulo: 'Preguntas frecuentes',
    descripcion: 'Se muestran en el centro de ayuda del sitio.',
    ruta: '/api/v1/admin/faqs',
    nombreItem: 'pregunta',
    buscarEn: ['pregunta', 'respuesta', 'slug'],
    columnas: [
      { key: 'orden', label: '#', align: 'right' },
      { key: 'pregunta', label: 'Pregunta' },
      { key: 'categoria_id', label: 'Categoría', hideSm: true, valor: (f) => categoria(f.categoria_id) },
      { key: 'activo', label: 'Estado', estado: true },
    ],
    campos: [
      { key: 'categoria_id', label: 'Categoría', tipo: 'select', opciones: opCategorias.value, requerido: true, soloCrear: true },
      { key: 'slug', label: 'Identificador', requerido: true, soloCrear: true, ayuda: 'minúsculas-y-guiones' },
      { key: 'pregunta', label: 'Pregunta', requerido: true, ancho: 'full' },
      { key: 'respuesta', label: 'Respuesta', tipo: 'textarea', requerido: true },
      { key: 'respuesta_corta_voz', label: 'Respuesta corta', tipo: 'textarea', ayuda: 'Máximo 400 caracteres' },
      { key: 'palabras_clave', label: 'Palabras clave', tipo: 'lista', ayuda: 'Separadas por comas' },
      { key: 'orden', label: 'Orden', tipo: 'number' },
      { key: 'activo', label: 'Visible', tipo: 'checkbox', soloEditar: true },
    ],
  },
}))
const config = computed(() => configs.value[seccion.value?.key ?? ''])
const query = computed(() => (seccion.value?.key === 'horarios' || seccion.value?.key === 'tarifas-pasaje') && filtroRuta.value ? { ruta_id: filtroRuta.value } : undefined)

const horariosDe = ref<{ id: number; codigo: string; nombre: string } | null>(null)
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Catálogos" subtitle="Datos maestros de la operación: red, flota, precios y contenido." />

    <SelectInput
      class="lg:hidden"
      label="Sección"
      :model-value="seccion?.key ?? null"
      :options="disponibles.map((s) => ({ value: s.key, label: `${s.grupo} · ${s.label}` }))"
      @update:model-value="ir"
    />

    <div class="grid items-start gap-6 lg:grid-cols-[230px_1fr]">
      <nav aria-label="Secciones de catálogos" class="hidden flex-col gap-4 lg:sticky lg:top-20 lg:flex">
        <div v-for="g in grupos" :key="g">
          <p class="mb-1.5 px-3 text-[11px] font-bold tracking-widest text-muted uppercase">{{ g }}</p>
          <RouterLink
            v-for="s in disponibles.filter((x) => x.grupo === g)"
            :key="s.key"
            :to="{ name: 'admin-catalogos', params: { seccion: s.key } }"
            replace
            class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
            :class="seccion?.key === s.key ? 'bg-surface font-semibold text-fg shadow-suave ring-1 ring-line' : 'text-muted hover:bg-surface-2 hover:text-fg'"
          >
            <component :is="s.icono" class="size-4" aria-hidden="true" />{{ s.label }}
          </RouterLink>
        </div>
      </nav>

      <div class="min-w-0">
        <PagesEditor v-if="seccion?.key === 'paginas'" />
        <ParametersSection v-else-if="seccion?.key === 'parametros'" />
        <CrudSection
          v-else-if="config"
          :key="config.ruta"
          :titulo="config.titulo"
          :descripcion="config.descripcion"
          :ruta="config.ruta"
          :columnas="config.columnas"
          :campos="config.campos"
          :paginado="config.paginado ?? true"
          :puede-crear="config.puedeCrear ?? true"
          :puede-editar="config.puedeEditar ?? true"
          :puede-eliminar="config.puedeEliminar ?? false"
          :nombre-item="config.nombreItem"
          :buscar-en="config.buscarEn"
          :query="query"
        >
          <template v-if="seccion?.key === 'horarios' || seccion?.key === 'tarifas-pasaje'" #filtros>
            <SelectInput v-model="filtroRuta" label="Ruta" class="w-60" :options="[{ value: null, label: 'Todas las rutas' }, ...opRutas]" />
          </template>
          <template v-if="seccion?.key === 'oficinas'" #acciones="{ fila }">
            <BaseButton size="sm" variant="ghost" icon-only aria-label="Horario de atención" title="Horario de atención" @click="horariosDe = { id: fila.id, codigo: fila.codigo, nombre: fila.nombre }">
              <CalendarClock class="size-4" />
            </BaseButton>
          </template>
        </CrudSection>
      </div>
    </div>

    <OfficeHoursDialog :oficina="horariosDe" @cerrar="horariosDe = null" />
  </div>
</template>
