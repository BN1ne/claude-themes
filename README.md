# Claude Themes

Temas para las apps de escritorio y móvil de Claude Code, con un comando para activarlos y desactivarlos.

## Temas

| Tema | Descripción |
| --- | --- |
| `mosaico` | Tiburones de mosaico ASCII (clásico, martillo y café moteado) que nadan en curvas sobre papel cuadriculado, con el cuerpo doblándose al girar, cardúmenes de rayitas y un resplandor alrededor del cuadro de texto. Modo claro. |

Los temas se ven en la app de escritorio y en el móvil. La terminal no dibuja temas.

## Instalación

En el prompt de una sesión de Claude Code:

```
/plugin install my-themes --marketplace BN1ne/claude-themes
```

Responde `y` para agregar el marketplace y elige el alcance (por ejemplo, para tu usuario).

Desde una terminal:

```bash
claude plugin install my-themes --marketplace BN1ne/claude-themes
```

## Uso

- `/my-themes`: lista los temas y cuál está activo.
- `/my-themes mosaico`: activa el tema animado.
- `/my-themes mosaico quieto`: activa la versión sin animación, que casi no consume recursos.
- `/my-themes off`: desactiva el tema y vuelve el aspecto normal de la app.

Tu elección se recuerda entre sesiones. Si Windows o macOS tienen activado "reducir movimiento", el fondo se queda quieto.

## Consumo de recursos

En la app de escritorio la escena es un shader que corre en la tarjeta gráfica a 30 cuadros por segundo. La forma de los tiburones se calcula una vez por celda de la cuadrícula, no por pixel. El validador estima unos 2 ms por cuadro en una tarjeta rápida y 8 ms en una débil.

Donde no hay shaders (el móvil, "reducir movimiento" o un equipo lento) la app muestra sola una versión SVG animada con CSS, que avanza a saltos. `/my-themes mosaico quieto` usa esa versión congelada, sin animación.

## Créditos

La técnica de dibujar los tiburones celda por celda, con la rampa de caracteres `:;t%SX8#@` y los cardúmenes de rayitas, está adaptada de [stackedlol/ascii-sharks](https://github.com/stackedlol/ascii-sharks) (MIT, Copyright (c) 2026 drewdi). El shader está en `hooks/mosaic-shader.ts` (con una vista previa en `tools/preview_mosaic_shader.py`) y la versión SVG se genera con `tools/gen_mosaic_scene.py`.

## Licencia

MIT. Ver `LICENSE`.
