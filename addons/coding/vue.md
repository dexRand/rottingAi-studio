# Add-on: Vue 3

Apply everything below unless the user asks otherwise.

## Method
- Change only what the task needs; keep the author's style, names, structure.
- Complete runnable code (imports included, no `...`, no invented APIs); for edits show only the changed block.
- Ambiguous request that changes code -> ask ONE short question; else state your default.

## Composition API
- Composition API first; Options API only if the project already uses it. Share logic with composables (`useX`) returning refs/functions, not mixins.
- `<script setup>` is the default SFC: top-level bindings reach the template; `defineProps`/`defineEmits`/`defineExpose` are macros (no import).
- `ref(x)` for primitives, `.value` in JS (auto-unwrapped in templates). `reactive(obj)` for objects; don't destructure it (loses reactivity) -> `toRefs`. `computed` for derived state (no side effects/async). `watch(source, cb, { immediate, deep })` for side effects; `watchEffect` when deps are implicit.
- Props down, events up: `defineProps<{ user: User }>()`, `defineEmits<{ save: [id: number] }>()`; never mutate props. `v-model` = `:modelValue` + `@update:modelValue`; `defineModel()` (3.4+) in custom components.
- Lifecycle: `onMounted` for DOM/external setup, `onUnmounted` for cleanup (timers, listeners), `onUpdated`/`onActivated` when needed.

## Router & state
- `vue-router`: `createRouter({ history: createWebHistory(), routes })`, `useRoute`/`useRouter`, `RouterLink`/`RouterView`, lazy routes `() => import('./View.vue')`; guards return `true`, a route, or `false`.
- `pinia`: setup store `defineStore('name', () => { ... return { state, getter, action } })`; `storeToRefs` when destructuring.
- `vite`: `npm create vite@latest`, `@vitejs/plugin-vue` in `vite.config.ts`, `@` alias for `src`; env via `import.meta.env.VITE_*`; `vite build`/`vite preview`.

## Pitfalls
- No `this` in `<script setup>`; don't destructure `props`/`reactive`; key `v-for` by a stable id; `v-if` before heavy `v-for`; sanitize `v-html`; clean up in `onUnmounted`.
