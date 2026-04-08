| Check | Status | Evidence |
|---|---|---|
| Active Node version | FAIL | v24.14.0 vs engines >=18 <=22 |
| Root .nvmrc pins Node 22 | PASS | .nvmrc=22 |
| Frontend .nvmrc pins Node 22 | PASS | frontend/.nvmrc=22 |
| Docker frontend build uses Node 22 | PASS | Dockerfile frontend stage |
| GitHub Actions uses Node 22 | PASS | .github/workflows |
| Repo has compliant path despite host Node | PASS | nvmrc + Docker + CI |
| Frontend tests | not_run | C:\Users\benxp\OneDrive\Documents\New project\proof\frontend_runtime_gate\frontend_test.log |
| Docker frontend build under Node 22 | passed | C:\Users\benxp\OneDrive\Documents\New project\proof\frontend_runtime_gate\docker_frontend_build.log |
