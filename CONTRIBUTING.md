# Contribuir a KnowLigo

¡Gracias por tu interés en contribuir! Este es un proyecto educativo/demo, pero las contribuciones son bienvenidas.

## Requisitos Previos

- Python 3.11+

## Flujo de Trabajo

1. **Fork** el repositorio
2. **Crear branch** desde `main`:
   ```bash
   git checkout -b feat/mi-feature
   ```
3. **Implementar** cambios siguiendo los patrones del proyecto
4. **Ejecutar tests** (todos deben pasar):
   ```bash
   py -3.11 -m pytest tests/ -v --tb=short
   ```
5. **Commit** usando [Conventional Commits](https://www.conventionalcommits.org/):
   ```
   feat: agregar soporte para imágenes en WhatsApp
   fix: corregir rate limit en pipeline RAG
   docs: actualizar diagramas de arquitectura
   test: agregar tests para flujo de contratación
   refactor: extraer lógica de validación a módulo separado
   ```
6. **Push** y crear **Pull Request** contra `main`

## Reglas de Código

- **Lenguaje del código**: Inglés (variables, funciones, clases)
- **Lenguaje de negocio**: Español (docstrings, comentarios, strings de usuario)
- **Type hints**: Obligatorios en todas las firmas de funciones
- **Docstrings**: En módulos, clases y funciones públicas
- **Logging**: Siempre `logger = logging.getLogger(__name__)` — nunca `print()`
- **Tests**: Todo cambio debe incluir tests. No se aceptan PRs que rompan tests existentes

## Estructura de PRs

- **Título**: Seguir Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- **Descripción**: Explicar qué cambia y por qué
- **Tests**: Indicar qué tests se agregaron o modificaron
- **Checklist**:
  - [ ] Los tests pasan (`pytest tests/ -v`)
  - [ ] Se respetan las reglas de dependencia entre capas
  - [ ] No hay `print()` en código runtime
  - [ ] No hay secrets hardcodeados

## Reglas de Dependencia

```
api/       → puede importar de agent/ y rag/query/
agent/     → puede importar de agent/ (interno) y rag/query/
rag/query/ → NO puede importar de agent/ ni de api/
```

## ¿Preguntas?

Abrí un Issue describiendo tu duda o propuesta antes de empezar a implementar.

## Licencia

Al contribuir, aceptás que tus contribuciones se licencian bajo [MIT](LICENSE).
