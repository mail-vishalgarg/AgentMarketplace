# Coding Rules

## Python / FastAPI
- **Thin routers.** FastAPI route functions call a service function and return its result. No business logic in routers.
- **Services own logic.** `app/services/` contains all business logic. Services are plain async functions or classes — no FastAPI imports.
- **Pydantic for all I/O.** Every request body, response model, and config value is a typed Pydantic model. Use `model_config = ConfigDict(extra="forbid")` on request models.
- **Typed Python.** All functions have full type annotations. `mypy --strict` must pass with zero errors.
- **Small functions.** If a function exceeds ~30 lines, split it. Name the extracted piece after what it does.
- **Tests for business logic.** Every service function that makes a decision has a pytest test. Routers are not unit-tested directly.

## React / TypeScript
- **Small components.** A component that exceeds ~80 lines of JSX should be split.
- **Typed props.** Every component defines a `Props` interface or type. No `any`.
- **No business logic in components.** Data-fetching lives in TanStack Query hooks (`useQuery`, `useMutation`). Transformation logic lives in plain functions in `src/lib/`.
- **Co-locate tests.** Test files sit next to the file they test (`Foo.test.tsx` beside `Foo.tsx`).

## Commits
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add agent publish endpoint
fix: correct JWT expiry calculation
chore: update dependencies
docs: add .env.example comments
```
Breaking changes use `feat!:` or `fix!:` with a `BREAKING CHANGE:` footer.
