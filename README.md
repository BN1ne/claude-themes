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

La escena es un SVG animado sin scripts. Cada tiburón se dibuja una vez, recto, y se corta en una tajada por columna de celdas. Cada tajada se mece arriba y abajo con un retraso que crece hacia la cola, así una onda recorre el cuerpo. El tiburón entero sigue una curva cerrada y suave (`animateMotion` con `rotate="auto"`), así gira donde gira la curva.

Con "reducir movimiento" la animación se detiene. `/my-themes mosaico quieto` usa una versión congelada, sin animación.

## Créditos

La técnica de dibujar los tiburones celda por celda, con la rampa de caracteres `:;t%SX8#@` y los cardúmenes de rayitas, está adaptada de [stackedlol/ascii-sharks](https://github.com/stackedlol/ascii-sharks) (MIT, Copyright (c) 2026 drewdi). La escena se genera con `python tools/gen_mosaic_scene.py hooks/mosaic-scene`. `hooks/mosaic-shader.ts` es una versión con shader que la app todavía no puede dibujar (no tiene elemento `Shader`); queda guardada pero no se carga.

## Licencia

MIT. Ver `LICENSE`.
