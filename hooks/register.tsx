import type { EngineInterface, Register, ThemeSetArgs } from 'claude-code'

import { makeColors } from './make-colors.js'
import { SCENE as MOSAIC, SCENE_STILL as MOSAIC_STILL } from './mosaic-scene'

// ── Temas ────────────────────────────────────────────────────────────────
// Para agregar uno: una entrada aquí con sus colores y sus escenas.

const mosaicColors = makeColors({
  label: 'Mosaico ASCII',
  only: 'light',
  roles: { accent: '#4a6585', danger: '#b23b35', success: '#4f7d4a', warning: '#a5701a', pro: '#6e5a96' },
  light: {
    gray: {
      anchors: {
        'surface-0': '#f2f2f0',
        'surface-1': '#f7f7f5',
        'surface-2': '#fbfbfa',
        'text-primary': '#1c1e22',
        'text-secondary': '#43474e',
        'text-muted': '#5d6169',
      },
    },
  },
})

type Theme = {
  name: string
  description: string
  colors: ReturnType<typeof makeColors>
  scene: string
  sceneStill: string
  alt: string
}

const THEMES: Record<string, Theme> = {
  mosaico: {
    name: 'Mosaico ASCII',
    description: 'tiburones de mosaico ASCII nadando sobre papel cuadriculado (claro)',
    colors: mosaicColors,
    scene: MOSAIC,
    sceneStill: MOSAIC_STILL,
    alt: 'Tiburones de mosaico ASCII nadando sobre papel cuadriculado',
  },
}

// ── Elección guardada entre sesiones ─────────────────────────────────────

type Choice = { id: string | null; still: boolean }
const DEFAULT: Choice = { id: 'mosaico', still: false }
const KEY = 'choice'

const readChoice = async ($: EngineInterface): Promise<Choice> => {
  const v = (await $.store.get(KEY)) as Partial<Choice> | undefined
  if (!v || typeof v !== 'object') return DEFAULT
  const id = v.id === null ? null : typeof v.id === 'string' && v.id in THEMES ? v.id : DEFAULT.id
  return { id, still: v.still === true }
}

const look = (theme: Theme, id: string, still: boolean): ThemeSetArgs => ({
  colors: theme.colors.theme,
  backdrop: {
    scene: `${id}${still ? '-still' : ''}`,
    glass: { blur: 6, tint: '#f7f7f5', opacity: 0.55 },
  },
})

const apply = async ($: EngineInterface, choice: Choice): Promise<string | undefined> => {
  if (choice.id === null) {
    await $.theme.clear()
    return undefined
  }
  const theme = THEMES[choice.id]
  if (!theme) return undefined
  const unpainted = theme.colors.problems.find(l => l.startsWith("Desktop won't paint"))
  if (unpainted !== undefined) $.ui.toast(unpainted)
  const set = await $.theme.set(look(theme, choice.id, choice.still))
  return set.isDrawn ? undefined : set.reason
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    await $.command.register({
      name: 'my-themes',
      description: 'Activa o desactiva tus temas: /my-themes, /my-themes mosaico [quieto], /my-themes off',
    })
    await apply($, await readChoice($))
    return result
  })

  on('command.run', { command: 'my-themes' }, async ($, e) => {
    const words = e.args.trim().toLowerCase().split(/\s+/).filter(Boolean)
    const current = await readChoice($)
    const list = Object.entries(THEMES)
      .map(([id, t]) => {
        const mark = current.id === id ? `  ← activo${current.still ? ' (quieto)' : ''}` : ''
        return `• ${id}: ${t.name}, ${t.description}${mark}`
      })
      .join('\n')

    if (words.length === 0) {
      const state = current.id === null ? 'Ningún tema activo.' : ''
      return {
        text: `Tus temas:\n${list}\n${state}\n\nUso: /my-themes <tema> [quieto] · /my-themes off`.replace('\n\n\n', '\n\n'),
      }
    }

    if (words[0] === 'off' || words[0] === 'apagar') {
      await $.store.set(KEY, { id: null, still: false })
      await apply($, { id: null, still: false })
      return { text: 'Tema desactivado. Escribe /my-themes mosaico para volver a activarlo.' }
    }

    const id = words[0] ?? ''
    const theme = THEMES[id]
    if (!theme) {
      return { text: `No tengo un tema llamado "${id}".\n${list}` }
    }
    const still = words.includes('quieto') || words.includes('still')
    const choice: Choice = { id, still }
    await $.store.set(KEY, choice)
    const reason = await apply($, choice)
    const done = `${theme.name} activado${still ? ' sin animación' : ''}.`
    return { text: reason ? `${done} Aviso: ${reason}` : done }
  })

  on('ui.render', { component: 'Backdrop' }, ($, e, next) => {
    if (e.surface !== 'desktop' && e.surface !== 'mobile') return next(e)
    const scene = String(e.props.scene ?? '')
    const still = scene.endsWith('-still')
    const theme = THEMES[still ? scene.slice(0, -6) : scene]
    if (!theme) return next(e)
    const { Svg } = $.ui.resolve(e)
    if (still) return <Svg source={theme.sceneStill} alt={theme.alt} />
    // La app no tiene elemento Shader: la escena viva es el Svg con su animación CSS.
    // isInteractive lo dibuja en un marco aislado, donde las animaciones corren.
    return <Svg source={theme.scene} alt={theme.alt} isInteractive />
  })
}
