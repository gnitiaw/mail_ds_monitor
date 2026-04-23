# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Quick Start section in root README with step-by-step setup guide
- `docker-compose.yml` with MySQL 8.0 for local development
- GitHub Actions CI workflow (ruff, pytest, eslint, tsc, vitest)
- Pre-commit hooks via husky + lint-staged
- Database connection health check at FastAPI startup
- Test coverage configuration (pytest --cov, vitest coverage)
- `.nvmrc` pinning Node.js 20

### Changed
- Root README rewritten from philosophy document to practical setup guide
- Seed script (`scripts/seed_pilot_data.py`) now documented in README

### Fixed
- Frontend Clay design system: menu labels, login hover, empty states, pagination styling
