# Claude Themes

Temas para las apps de escritorio y móvil de Claude Code, con un comando para activarlos y desactivarlos.

## Temas

| Tema | Descripción |
| --- | --- |
| `mosaico` | Tiburones de mosaico ASCII que nadan sobre papel cuadriculado, con un resplandor suave al centro. Modo claro. |

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

El fondo es un SVG animado solo con CSS, sin JavaScript. Todo avanza a saltos de cuadrícula: unos pocos redibujos por segundo, no 60.

## Créditos

La técnica de dibujar los tiburones celda por celda, con la rampa de caracteres `:;t%SX8#@` y los cardúmenes de rayitas, está adaptada de [stackedlol/ascii-sharks](https://github.com/stackedlol/ascii-sharks) (MIT, Copyright (c) 2026 drewdi). La escena se genera con `tools/gen_mosaic_scene.py`.

## Licencia

MIT. Ver `LICENSE`.
