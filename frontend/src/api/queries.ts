import { useQuery } from '@tanstack/vue-query'
import { api, unwrap } from './client'

const LARGO = 10 * 60_000 // catálogos: cambian poco

export function useEmpresa() {
  return useQuery({ queryKey: ['empresa'], queryFn: () => unwrap(api.GET('/api/v1/empresa')), staleTime: LARGO })
}

export function useCiudades(filtro?: { pasajeros?: boolean; carga?: boolean }) {
  return useQuery({
    queryKey: ['ciudades', filtro ?? {}],
    queryFn: () => unwrap(api.GET('/api/v1/ciudades', { params: { query: filtro ?? {} } })),
    staleTime: LARGO,
  })
}

export function useRutas() {
  return useQuery({ queryKey: ['rutas'], queryFn: () => unwrap(api.GET('/api/v1/rutas')), staleTime: LARGO })
}

export function useTiposAsiento() {
  return useQuery({
    queryKey: ['tipos-asiento'],
    queryFn: () => unwrap(api.GET('/api/v1/tipos-asiento')),
    staleTime: LARGO,
  })
}

export function usePoliticas() {
  return useQuery({ queryKey: ['politicas'], queryFn: () => unwrap(api.GET('/api/v1/politicas')), staleTime: LARGO })
}

export function useFeriados() {
  return useQuery({ queryKey: ['feriados'], queryFn: () => unwrap(api.GET('/api/v1/feriados')), staleTime: LARGO })
}

export function useOficinasPublicas() {
  return useQuery({ queryKey: ['oficinas'], queryFn: () => unwrap(api.GET('/api/v1/oficinas')), staleTime: LARGO })
}
