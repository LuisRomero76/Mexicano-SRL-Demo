<script setup lang="ts">
import { computed, ref } from 'vue'
import { useOficinasPublicas } from '@/api/queries'
import CrudSection, { type CampoCrud, type ColumnaCrud } from '@/components/admin/CrudSection.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectInput from '@/components/ui/SelectInput.vue'
import SurfaceCard from '@/components/ui/SurfaceCard.vue'
import { fechaHora, telefono } from '@/lib/format'
import { ROL } from '@/lib/labels'
import { SOLO_ADMIN } from '@/lib/roles'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const esAdmin = computed(() => auth.puede(SOLO_ADMIN))
const { data: oficinas } = useOficinasPublicas()
const rol = ref<string | null>(null)

const opRoles = Object.entries(ROL).map(([value, label]) => ({ value, label }))
const opOficinas = computed(() => [{ value: null, label: 'Sin oficina fija' }, ...(oficinas.value ?? []).map((o) => ({ value: o.oficina_id, label: `${o.ciudad} · ${o.nombre}` }))])
const oficina = (id: number | null) => oficinas.value?.find((o) => o.oficina_id === id)?.nombre ?? '—'

const columnas: ColumnaCrud[] = [
  { key: 'nombre', label: 'Nombre', valor: (u) => `${u.nombres} ${u.apellidos}` },
  { key: 'email', label: 'Correo', hideSm: true },
  { key: 'rol', label: 'Rol', valor: (u) => ROL[u.rol] ?? u.rol },
  { key: 'oficina_id', label: 'Oficina', hideSm: true, valor: (u) => oficina(u.oficina_id) },
  { key: 'telefono_e164', label: 'Teléfono', hideSm: true, valor: (u) => telefono(u.telefono_e164) },
  { key: 'ultimo_login_at', label: 'Último ingreso', hideSm: true, valor: (u) => (u.ultimo_login_at ? fechaHora(u.ultimo_login_at) : 'Nunca') },
  { key: 'activo', label: 'Estado', estado: true },
]
const campos = computed<CampoCrud[]>(() => [
  { key: 'email', label: 'Correo', tipo: 'email', requerido: true, soloCrear: true, ancho: 'full' },
  { key: 'nombres', label: 'Nombres', requerido: true },
  { key: 'apellidos', label: 'Apellidos', requerido: true },
  { key: 'rol', label: 'Rol', tipo: 'select', opciones: opRoles, requerido: true },
  { key: 'oficina_id', label: 'Oficina', tipo: 'select', opciones: opOficinas.value },
  { key: 'telefono_e164', label: 'Celular', ayuda: 'Formato +591…' },
  { key: 'licencia_conducir', label: 'Licencia de conducir', ayuda: 'Solo conductores' },
  { key: 'password', label: 'Contraseña', tipo: 'password', requerido: true, soloCrear: true, ayuda: 'Mínimo 10 caracteres, con letras y números', ancho: 'full' },
  { key: 'password', label: 'Nueva contraseña', tipo: 'password', soloEditar: true, ayuda: 'Déjala vacía para no cambiarla', ancho: 'full' },
  { key: 'activo', label: 'Cuenta activa', tipo: 'checkbox', soloEditar: true, ayuda: 'Una cuenta inactiva no puede ingresar' },
])

const PERMISOS: { rol: string; puede: string }[] = [
  { rol: 'Administrador', puede: 'Todo, incluidos el personal y los parámetros del sistema.' },
  { rol: 'Supervisor', puede: 'Operación completa: salidas, ventas, reembolsos, carga, catálogos, reportes y auditoría.' },
  { rol: 'Boletería', puede: 'Venta en ventanilla, abordaje y consulta de ventas.' },
  { rol: 'Bodega', puede: 'Registro, despacho y entrega de encomiendas; puerta a puerta.' },
  { rol: 'Repartidor', puede: 'Sus entregas y recojos puerta a puerta.' },
  { rol: 'Conductor', puede: 'Salidas asignadas y abordaje.' },
  { rol: 'Soporte', puede: 'Reembolsos, puerta a puerta, preguntas frecuentes y páginas del sitio.' },
]
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageHeader title="Personal" :subtitle="esAdmin ? 'Cuentas del personal y sus permisos.' : 'Consulta del personal. Solo el administrador crea o modifica cuentas.'" />
    <div class="grid items-start gap-6 xl:grid-cols-[1fr_320px]">
      <CrudSection
        titulo="Cuentas"
        ruta="/api/v1/admin/usuarios"
        nombre-item="usuario"
        :columnas="columnas"
        :campos="campos"
        :puede-crear="esAdmin"
        :puede-editar="esAdmin"
        :query="rol ? { rol } : undefined"
      >
        <template #filtros>
          <SelectInput v-model="rol" label="Rol" class="w-48" :options="[{ value: null, label: 'Todos los roles' }, ...opRoles]" />
        </template>
      </CrudSection>
      <SurfaceCard title="Roles y permisos" subtitle="El servidor aplica estos permisos en cada operación.">
        <dl class="flex flex-col gap-3 text-sm">
          <div v-for="p in PERMISOS" :key="p.rol">
            <dt class="font-semibold">{{ p.rol }}</dt>
            <dd class="text-muted">{{ p.puede }}</dd>
          </div>
        </dl>
      </SurfaceCard>
    </div>
  </div>
</template>
