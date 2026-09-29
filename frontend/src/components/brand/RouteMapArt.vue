<script setup lang="ts">
/** Mapa estilizado de las rutas reales: todas salen de Sucre. Las paradas de carga van punteadas. */
</script>

<template>
  <svg viewBox="0 0 520 380" class="h-auto w-full" role="img" aria-labelledby="mapa-titulo">
    <title id="mapa-titulo">Mapa de rutas: Sucre conecta con Santa Cruz, La Paz y Tarija</title>
    <g fill="none" stroke="#1B3358" stroke-width="1">
      <path d="M0 60 H520 M0 140 H520 M0 220 H520 M0 300 H520 M90 0 V380 M210 0 V380 M330 0 V380 M450 0 V380" />
    </g>
    <g fill="none" stroke="#E0314F" stroke-width="3" stroke-linecap="round" class="rutas">
      <path d="M250 220 C 320 170, 380 160, 440 150" />
      <path d="M250 220 C 180 170, 140 110, 110 80" />
      <path d="M250 220 C 240 270, 255 310, 270 350" />
    </g>
    <path d="M250 220 L 214 246 L 244 300" fill="none" stroke="#7D8FB0" stroke-width="1.5" stroke-dasharray="4 5" />
    <path d="M110 80 L 92 70" fill="none" stroke="#7D8FB0" stroke-width="1.5" stroke-dasharray="4 5" />
    <circle cx="250" cy="220" r="18" fill="#E0314F" opacity="0.18" class="pulso" />
    <circle cx="250" cy="220" r="11" fill="#E0314F" />
    <circle cx="250" cy="220" r="5" fill="#fff" />
    <circle cx="440" cy="150" r="7" fill="#fff" />
    <circle cx="110" cy="80" r="7" fill="#fff" />
    <circle cx="270" cy="350" r="7" fill="#fff" />
    <circle cx="214" cy="246" r="4.5" fill="#7D8FB0" />
    <circle cx="244" cy="300" r="4.5" fill="#7D8FB0" />
    <circle cx="92" cy="70" r="4.5" fill="#7D8FB0" />
    <g font-family="Public Sans Variable, sans-serif" font-size="14" fill="#fff" font-weight="600">
      <text x="270" y="214">Sucre</text>
      <text x="400" y="132">Santa Cruz</text>
      <text x="126" y="98">La Paz</text>
      <text x="286" y="355">Tarija</text>
    </g>
    <g font-family="Public Sans Variable, sans-serif" font-size="12" fill="#9FB0CC">
      <text x="150" y="250">Potosí</text>
      <text x="176" y="306">Camargo</text>
      <text x="36" y="58">El Alto</text>
      <text x="336" y="206">661 km · 14 h</text>
      <text x="104" y="162">555 km · 12 h</text>
      <text x="168" y="334">469 km · 11 h</text>
    </g>
  </svg>
</template>

<style scoped>
.rutas path {
  stroke-dasharray: 400;
  stroke-dashoffset: 400;
  animation: trazar 0.9s ease-out forwards;
}
.rutas path:nth-child(2) {
  animation-delay: 0.2s;
}
.rutas path:nth-child(3) {
  animation-delay: 0.4s;
}
.pulso {
  transform-origin: 250px 220px;
  animation: pulso 2.4s ease-out infinite;
}
@keyframes trazar {
  to {
    stroke-dashoffset: 0;
  }
}
@keyframes pulso {
  0% {
    transform: scale(0.6);
    opacity: 0.35;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}
</style>
