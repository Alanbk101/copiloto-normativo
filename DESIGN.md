---
name: Copiloto Normativo
description: RAG de citación exacta sobre documentos regulatorios mexicanos
colors:
  guinda: "#6E1423"
  papel: "#F6F5F1"
  tinta: "#111110"
  masa: "#3A3530"
  linea: "#D8D4CC"
  cita: "#EDECE7"
typography:
  display:
    fontFamily: "Spectral, Georgia, serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Spectral, Georgia, serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0"
rounded:
  none: "0px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "20px"
  lg: "32px"
  xl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.guinda}"
    textColor: "{colors.papel}"
    rounded: "{rounded.none}"
    padding: "8px 20px"
  button-primary-hover:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.guinda}"
    rounded: "{rounded.none}"
  upload-zone:
    backgroundColor: "{colors.papel}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.none}"
    padding: "40px 24px"
  source-card:
    backgroundColor: "{colors.cita}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
---

# Design System: Copiloto Normativo

## Overview

**Creative North Star: "El Expediente Oficial"**

Copiloto Normativo no es una aplicación de chat — es un instrumento documental. La interfaz emula la estructura de un expediente regulatorio mexicano: encabezados numerados con símbolo de sección (§), tipografía de publicación oficial, superficies de papel envejecido y un acento guinda que no se derrama. Cada elemento visual dice "esto es un documento de autoridad", antes de que el usuario lea una sola línea de contenido.

La densidad es funcional, no decorativa. Los márgenes anchos, los divisores sin peso y el blanco entre secciones existen para que el ojo localice información rápidamente — igual que en un reglamento bien tipografiado. La Spectral (serif de lectura extendida) aparece exactamente donde aparece en una publicación legal: en el texto de respuesta del LLM, que se lee como un extracto de documento, no como un mensaje de chat.

La paleta es una elección editorial estricta: guinda oscuro sobre papel marfil, con masas de texto en café-gris. No hay color decorativo. La voz del sistema es precisa, directa y sin eufemismos — refleja que el dominio no admite ambigüedad.

**Key Characteristics:**
- Geometría completamente rectilineal — cero border-radius en toda la interfaz
- Acento guinda estrictamente reservado: marcadores de sección, bordes de autoridad, botón primario, focus ring
- Tipografía dual con propósito semántico: Spectral para contenido documental, IBM Plex Sans para UI
- Profundidad por borde izquierdo, no por sombra
- Terminología de expediente (§1, §2, "Fuentes citadas") — no terminología de producto SaaS

## Colors

Paleta editorial en tres roles: acento de autoridad (guinda), superficies neutras (papel, cita), y jerarquía de texto (tinta, masa, linea).

### Primary
- **Guinda DOF** (#6E1423): El único color de acento. Usado en marcadores de sección (§1, §2), bordes izquierdos de autoridad (source cards), botón primario, focus ring, y estados de drag-hover. Su rareza es la que le da peso.

### Neutral
- **Papel Marfil** (#F6F5F1): Superficie base de toda la aplicación. Evoca papel de archivo ligeramente envejecido, no blanco digital.
- **Tinta** (#111110): Texto primario — casi negro, con temperatura levemente cálida para armonizar con papel.
- **Masa** (#3A3530): Texto secundario y metadatos. Café-gris que recede sin desaparecer.
- **Linea** (#D8D4CC): Divisores, bordes de reposo, separadores de columna. Línea de grilla documental.
- **Cita** (#EDECE7): Fondo de source cards. Ligeramente más oscuro que papel — diferencia tonal mínima que agrupa el material citado sin usar color.

### Named Rules
**The One Accent Rule.** El guinda aparece en ≤ 3 elementos visibles simultáneamente. Nunca como color de fondo de superficie completa, nunca en texto de párrafo. Su aparición señala autoridad o acción; usarlo más diluye la señal.

**The No-Color Rule.** Los estados de error usan rojo (#dc2626); los de advertencia, ámbar (#d97706). Ningún otro color entra al sistema. No hay gradientes, no hay colores de acento adicionales.

## Typography

**Display Font:** Spectral (con fallback Georgia, serif)
**Body Font:** IBM Plex Sans (con fallback system-ui, sans-serif)

**Carácter:** Spectral es una serif de lectura extendida diseñada para pantalla — su apertura y ritmo hacen que el texto LLM (respuestas de varios párrafos) sea legible sin fatiga. IBM Plex Sans aporta precisión técnica y neutralidad para la UI: etiquetas, metadatos, controles. El contraste entre ambas familias no es decorativo — marca la frontera entre interfaz y contenido documental.

### Hierarchy
- **Display** (Spectral, 600, 1.875rem / 30px, tracking −0.025em): Título principal "Copiloto Normativo". Aparece una sola vez por pantalla.
- **Headline** (IBM Plex Sans, 500, 0.875rem / 14px): Encabezados de sección con marcador §. Etiqueta de autoridad, no titular editorial.
- **Body documental** (Spectral, 400, 1rem / 16px, leading 1.6): Respuesta del LLM. La única instancia de Spectral en tamaño de lectura — señala que este texto es contenido, no interfaz.
- **Body UI** (IBM Plex Sans, 400, 0.875rem / 14px, leading 1.6): Texto de instrucción, nombres de archivo, contenido de input. Máximo ~65ch de ancho efectivo en columna principal.
- **Label** (IBM Plex Sans, 500, 0.75rem / 12px): Metadatos, contadores, estados. Tabular-nums para cifras alineadas.

### Named Rules
**The Two-Font Rule.** Solo Spectral y IBM Plex Sans. Spectral exclusivamente en: nombre del producto (h1), respuesta del LLM, texto de número de sección con marcador §. IBM Plex Sans en todo lo demás. No hay excepciones.

## Layout

Contenedor centrado max-w-5xl con padding horizontal responsive: 24px (móvil), 40px (sm), 64px (lg). Padding vertical 48px superior.

En pantallas lg+ (≥ 1024px): grid de dos columnas `2fr / 3fr` separadas por una línea vertical (border-l, 1px, linea). §1 Expediente en la columna angosta, §2 Consulta en la ancha. La proporción 2:3 refleja que la consulta es la acción principal; el expediente es el contexto.

En pantallas menores: columna única, §1 arriba / §2 abajo, separadas por border-b (linea). La jerarquía de lectura se preserva: primero el material, luego la consulta.

Espaciado de ritmo vertical: 24px entre bloques relacionados (mt-6), 48px entre secciones mayores (mb-10, pb-12). La grilla de 8px es el denominador común (py-3 = 12px, px-4 = 16px, space-y-6 = 24px).

## Elevation & Depth

Sistema completamente plano. No existe ningún box-shadow en la interfaz. La profundidad se comunica exclusivamente por dos mecanismos:

1. **Borde izquierdo de autoridad** (border-l-2, 2px, guinda): Source cards, bloques de respuesta del LLM, estados de error/advertencia. El grosor 2px y el color guinda confieren jerarquía sin elevar físicamente el elemento.
2. **Diferencia tonal de superficie** (papel #F6F5F1 vs. cita #EDECE7): Source cards se distinguen del fondo por ~4 puntos de lightness. Agrupación silenciosa, sin borde ni sombra.

### Named Rules
**The Flat Authority Rule.** La jerarquía se establece con bordes, no con elevación. Un elemento más importante que su contexto recibe un borde izquierdo en guinda, no una sombra o una tarjeta flotante.

## Shapes

Geometría completamente rectilineal. Border-radius: 0px en todos los componentes — botones, inputs, upload zone, source cards, status badges, focus rings.

Esta decisión no es omisión — es la declaración de que el sistema es un instrumento formal, no un producto de consumo. Los documentos regulatorios no tienen esquinas redondeadas.

Los bordes son finos (1px linea en reposo, 2px guinda en estado de autoridad/énfasis). No hay outline, no hay ring visible en reposo — solo en focus-visible (2px guinda, offset 2px), para accesibilidad sin ruido visual en estado neutro.

## Components

### Botón primario (Preguntar)
Instrumento de acción, no de persuasión. Diseñado para ser reconocible en una interfaz sin color, no para competir visualmente.

- **Shape:** rectilineal (border-radius: 0)
- **Reposo:** bg-guinda text-papel, px-5 py-2, text-sm font-medium
- **Hover:** inversión completa — bg-papel text-guinda, border border-guinda. Transición de color.
- **Focus:** ring-2 ring-guinda ring-offset-2 ring-offset-papel
- **Disabled:** opacity-50, cursor-not-allowed. Sin cambio de forma.

### Zona de upload
- **Shape:** rectilineal, px-6 py-10
- **Reposo:** border border-linea (1px)
- **Drag-hover:** border-guinda bg-guinda/5 — el único uso de alpha en toda la interfaz
- **Uploading:** opacity-60, cursor-not-allowed
- **Contenido:** texto instructivo en tinta/masa, enlace subrayado en guinda

### Textarea de consulta
- **Shape:** rectilineal, sin resize, w-full
- **Reposo:** border border-linea bg-papel
- **Focus:** border-guinda focus:ring-1 focus:ring-guinda/20 — foco suave, no agresivo
- **Disabled:** opacity-60, cursor-not-allowed
- **Placeholder:** masa/50 (50% opacidad) — presente pero recede

### Source Card (componente firma)
El componente más distinctivo del sistema. Evoca la estructura de un artículo numerado en el DOF.

- **Layout:** flex horizontal — columna de número a la izquierda, contenido a la derecha
- **Número:** tabular-nums font-semibold text-guinda — el único texto guinda de todo el sistema aparte de los marcadores §
- **Borde izquierdo:** border-l-2 border-l-guinda — señala que este fragmento tiene autoridad citada
- **Fondo:** bg-cita (#EDECE7) — diferencia tonal mínima respecto al papel
- **Ruta + página:** flex items-baseline con leader-dot dashes (border-b border-dashed border-linea) entre nombre del artículo y número de página — patrón de tabla de contenidos
- **Animación:** fade-up con delay escalonado (index × 80ms) — las citas llegan secuencialmente, no en bloque

### Lista de documentos
- Lista vertical dividida por líneas (divide-y divide-linea)
- Cada ítem: py-3, nombre truncado en flex-1, badge de estado a la derecha
- Status badge: rectilineal, px-2 py-0.5, text-xs font-medium
  - completed: text-guinda bg-guinda/10
  - pending/processing: text-masa bg-linea/60
  - failed: text-red-700 bg-red-50
- Spinner inline en guinda para estados activos

### Bloque de respuesta (AnswerDisplay)
- Respuesta del LLM: border-l border-linea pl-5 py-1 — borde fino de linea (no guinda), la respuesta es contenido, no elemento de UI
- Texto en Spectral font-serif leading-relaxed — el único cuerpo de texto en serif
- "No encontrado": border-l-2 border-l-amber-600 — cambio de grosor y color señala estado de ausencia sin error

### Estados informativos (left-border pattern)
Todos los estados de sistema usan el mismo patrón: borde izquierdo de 2px en color semántico, padding izquierdo, sin fondo de color saturado.

- **Cargando:** border-l-masa, texto: font-medium text-tinta + text-xs text-masa
- **Error:** border-l-red-700, texto: text-red-800 + text-red-700
- **Advertencia/no encontrado:** border-l-amber-600, texto: text-amber-800 + text-amber-700
- **Autoridad/cita:** border-l-guinda (2px) — la única instancia positiva del patrón

## Do's and Don'ts

### Do:
- **Do** usar guinda exclusivamente en: marcadores §, bordes de source card, botón primario, focus ring, número de cita, enlace de upload. Esos son los únicos sitios válidos.
- **Do** usar Spectral en: título h1, respuestas del LLM, símbolo § en encabezados de sección. Usar IBM Plex Sans en todo lo demás.
- **Do** mantener border-radius: 0 en todos los componentes nuevos. La rectilinealidad es una decisión semántica, no estética.
- **Do** usar el patrón de borde izquierdo (border-l-2) para comunicar jerarquía y estado — es el lenguaje de profundidad del sistema.
- **Do** usar animación fade-up (0.3s ease-out) y delay escalonado cuando elementos de lista aparecen después de una operación asíncrona.

### Don't:
- **Don't** añadir border-radius a ningún componente. Ni siquiera rounded-sm para "suavizar".
- **Don't** usar guinda como color de texto de párrafo o como fondo de superficie amplia.
- **Don't** añadir sombras (box-shadow) — el sistema es plano por decisión explícita.
- **Don't** introducir una tercera familia tipográfica. La tensión Spectral/IBM Plex Sans es el sistema; una tercera fuente la rompe.
- **Don't** usar terminología de producto SaaS en la UI — no "Upload", no "Chat", no "Submit". El vocabulario es: Expediente, Consulta, Preguntar, Fuentes citadas, fragmentos indexados.
- **Don't** usar color de fondo saturado para estados de error/advertencia — solo el borde izquierdo lleva el color semántico.
