"""
Microservice Scaffold Service

Generates complete microservice project structures with
best practices for various languages and frameworks.
"""

import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional

from Asgard.Volundr.Scaffold.models.scaffold_models import (
    ServiceConfig,
    ScaffoldReport,
    FileEntry,
    Language,
    Framework,
    ProjectType,
)


class MicroserviceScaffold:
    """Generates microservice project structures."""

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the microservice scaffold.

        Args:
            output_dir: Directory for saving generated projects
        """
        self.output_dir = output_dir or "."

    def generate(self, config: ServiceConfig) -> ScaffoldReport:
        """
        Generate a microservice project structure.

        Args:
            config: Service configuration

        Returns:
            ScaffoldReport with generated files
        """
        scaffold_id = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:16]

        files: List[FileEntry] = []
        directories: List[str] = []
        messages: List[str] = []

        # Generate based on language
        if config.language == Language.PYTHON:
            files, directories = self._generate_python_service(config)
        elif config.language == Language.TYPESCRIPT:
            files, directories = self._generate_typescript_service(config)
        elif config.language == Language.GO:
            files, directories = self._generate_go_service(config)
        else:
            messages.append(f"Language {config.language.value} scaffolding not yet implemented")
            files, directories = self._generate_generic_service(config)

        # Add common files
        files.extend(self._generate_common_files(config))

        next_steps = self._get_next_steps(config)

        return ScaffoldReport(
            id=f"microservice-{scaffold_id}",
            project_name=config.name,
            project_type=config.project_type.value,
            files=files,
            directories=directories,
            total_files=len(files),
            total_directories=len(directories),
            created_at=datetime.now(),
            messages=messages,
            next_steps=next_steps,
        )

    def _generate_python_service(
        self, config: ServiceConfig
    ) -> tuple[List[FileEntry], List[str]]:
        """Generate Python microservice structure."""
        files: List[FileEntry] = []
        directories: List[str] = [
            f"{config.name}",
            f"{config.name}/app",
            f"{config.name}/app/routers",
            f"{config.name}/app/services",
            f"{config.name}/app/models",
            f"{config.name}/app/config",
        ]

        if config.include_tests:
            directories.append(f"{config.name}/tests")
            directories.append(f"{config.name}/tests/unit")
            directories.append(f"{config.name}/tests/integration")

        # pyproject.toml
        files.append(FileEntry(
            path=f"{config.name}/pyproject.toml",
            content=self._python_pyproject_toml(config),
        ))

        # requirements.txt
        files.append(FileEntry(
            path=f"{config.name}/requirements.txt",
            content=self._python_requirements(config),
        ))

        # Main application
        if config.framework == Framework.FASTAPI:
            files.append(FileEntry(
                path=f"{config.name}/app/main.py",
                content=self._python_fastapi_main(config),
            ))
        else:
            files.append(FileEntry(
                path=f"{config.name}/app/main.py",
                content=self._python_generic_main(config),
            ))

        # __init__.py files
        for d in ["app", "app/routers", "app/services", "app/models", "app/config"]:
            files.append(FileEntry(
                path=f"{config.name}/{d}/__init__.py",
                content="",
            ))

        # Config
        files.append(FileEntry(
            path=f"{config.name}/app/config/settings.py",
            content=self._python_settings(config),
        ))

        # Health router
        if config.include_healthcheck:
            files.append(FileEntry(
                path=f"{config.name}/app/routers/health.py",
                content=self._python_health_router(config),
            ))

        # Tests
        if config.include_tests:
            files.append(FileEntry(
                path=f"{config.name}/tests/__init__.py",
                content="",
            ))
            files.append(FileEntry(
                path=f"{config.name}/tests/conftest.py",
                content=self._python_conftest(config),
            ))
            files.append(FileEntry(
                path=f"{config.name}/tests/unit/__init__.py",
                content="",
            ))
            files.append(FileEntry(
                path=f"{config.name}/tests/unit/test_health.py",
                content=self._python_test_health(config),
            ))

        # Dockerfile
        if config.include_docker:
            files.append(FileEntry(
                path=f"{config.name}/Dockerfile",
                content=self._python_dockerfile(config),
            ))

        return files, directories

    def _generate_typescript_service(
        self, config: ServiceConfig
    ) -> tuple[List[FileEntry], List[str]]:
        """Generate TypeScript microservice structure."""
        files: List[FileEntry] = []
        directories: List[str] = [
            f"{config.name}",
            f"{config.name}/src",
            f"{config.name}/src/routes",
            f"{config.name}/src/services",
            f"{config.name}/src/models",
            f"{config.name}/src/config",
        ]

        if config.include_tests:
            directories.append(f"{config.name}/tests")

        # package.json
        files.append(FileEntry(
            path=f"{config.name}/package.json",
            content=self._typescript_package_json(config),
        ))

        # tsconfig.json
        files.append(FileEntry(
            path=f"{config.name}/tsconfig.json",
            content=self._typescript_tsconfig(config),
        ))

        # Main entry
        files.append(FileEntry(
            path=f"{config.name}/src/index.ts",
            content=self._typescript_index(config),
        ))

        # Config
        files.append(FileEntry(
            path=f"{config.name}/src/config/index.ts",
            content=self._typescript_config(config),
        ))

        # Health route
        if config.include_healthcheck:
            files.append(FileEntry(
                path=f"{config.name}/src/routes/health.ts",
                content=self._typescript_health_route(config),
            ))

        # Dockerfile
        if config.include_docker:
            files.append(FileEntry(
                path=f"{config.name}/Dockerfile",
                content=self._typescript_dockerfile(config),
            ))

        return files, directories

    def _generate_go_service(
        self, config: ServiceConfig
    ) -> tuple[List[FileEntry], List[str]]:
        """Generate Go microservice structure."""
        files: List[FileEntry] = []
        directories: List[str] = [
            f"{config.name}",
            f"{config.name}/cmd",
            f"{config.name}/cmd/server",
            f"{config.name}/internal",
            f"{config.name}/internal/handlers",
            f"{config.name}/internal/services",
            f"{config.name}/internal/config",
            f"{config.name}/pkg",
        ]

        if config.include_tests:
            directories.append(f"{config.name}/internal/handlers")

        # go.mod
        files.append(FileEntry(
            path=f"{config.name}/go.mod",
            content=self._go_mod(config),
        ))

        # Main entry
        files.append(FileEntry(
            path=f"{config.name}/cmd/server/main.go",
            content=self._go_main(config),
        ))

        # Config
        files.append(FileEntry(
            path=f"{config.name}/internal/config/config.go",
            content=self._go_config(config),
        ))

        # Health handler
        if config.include_healthcheck:
            files.append(FileEntry(
                path=f"{config.name}/internal/handlers/health.go",
                content=self._go_health_handler(config),
            ))

        # Dockerfile
        if config.include_docker:
            files.append(FileEntry(
                path=f"{config.name}/Dockerfile",
                content=self._go_dockerfile(config),
            ))

        return files, directories

    def _generate_generic_service(
        self, config: ServiceConfig
    ) -> tuple[List[FileEntry], List[str]]:
        """Generate generic service structure."""
        files: List[FileEntry] = []
        directories: List[str] = [
            f"{config.name}",
            f"{config.name}/src",
        ]

        files.append(FileEntry(
            path=f"{config.name}/README.md",
            content=f"# {config.name}\n\n{config.description}\n",
        ))

        return files, directories

    def _generate_common_files(self, config: ServiceConfig) -> List[FileEntry]:
        """Generate common files for all services."""
        files: List[FileEntry] = []

        # README
        files.append(FileEntry(
            path=f"{config.name}/README.md",
            content=self._readme(config),
        ))

        # .gitignore
        files.append(FileEntry(
            path=f"{config.name}/.gitignore",
            content=self._gitignore(config),
        ))

        # .env.example
        files.append(FileEntry(
            path=f"{config.name}/.env.example",
            content=self._env_example(config),
        ))

        # docker-compose for local development
        if config.include_docker:
            files.append(FileEntry(
                path=f"{config.name}/docker-compose.yaml",
                content=self._docker_compose(config),
            ))

        return files

    # Python templates
    def _python_pyproject_toml(self, config: ServiceConfig) -> str:
        return f'''[project]
name = "{config.name}"
version = "0.1.0"
description = "{config.description}"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
'''

    def _python_requirements(self, config: ServiceConfig) -> str:
        deps = []
        if config.framework == Framework.FASTAPI:
            deps.extend(["fastapi>=0.109.0", "uvicorn[standard]>=0.27.0"])
        deps.extend(["pydantic>=2.5.0", "pydantic-settings>=2.1.0"])
        if config.include_logging:
            deps.append("structlog>=24.1.0")
        if config.include_tests:
            deps.extend(["pytest>=7.4.0", "pytest-asyncio>=0.23.0", "httpx>=0.26.0"])
        return "\n".join(deps) + "\n"

    def _python_fastapi_main(self, config: ServiceConfig) -> str:
        imports = "from fastapi import FastAPI"
        if config.include_healthcheck:
            imports += "\nfrom app.routers import health"

        routers = ""
        if config.include_healthcheck:
            routers = '\napp.include_router(health.router, prefix="/health", tags=["health"])'

        return f'''{imports}

app = FastAPI(
    title="{config.name}",
    description="{config.description}",
    version="0.1.0",
)
{routers}

@app.get("/")
async def root():
    return {{"message": "Welcome to {config.name}"}}
'''

    def _python_generic_main(self, config: ServiceConfig) -> str:
        return f'''"""
{config.name} - Main Application
"""


def main():
    print("Starting {config.name}")


if __name__ == "__main__":
    main()
'''

    def _python_settings(self, config: ServiceConfig) -> str:
        return f'''from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "{config.name}"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = {config.port}

    class Config:
        env_file = ".env"


settings = Settings()
'''

    def _python_health_router(self, config: ServiceConfig) -> str:
        return '''from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    return {"status": "alive"}
'''

    def _python_conftest(self, config: ServiceConfig) -> str:
        return '''import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
'''

    def _python_test_health(self, config: ServiceConfig) -> str:
        return '''def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_check(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
'''

    def _python_dockerfile(self, config: ServiceConfig) -> str:
        return f'''FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos '' appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE {config.port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{config.port}/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{config.port}"]
'''

    # TypeScript templates
    def _typescript_package_json(self, config: ServiceConfig) -> str:
        return f'''{{
  "name": "{config.name}",
  "version": "0.1.0",
  "description": "{config.description}",
  "main": "dist/index.js",
  "scripts": {{
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node-dev --respawn src/index.ts",
    "test": "jest",
    "lint": "eslint src --ext .ts"
  }},
  "dependencies": {{
    "express": "^4.18.0",
    "dotenv": "^16.3.0"
  }},
  "devDependencies": {{
    "@types/express": "^4.17.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "ts-node-dev": "^2.0.0"
  }}
}}
'''

    def _typescript_tsconfig(self, config: ServiceConfig) -> str:
        return '''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
'''

    def _typescript_index(self, config: ServiceConfig) -> str:
        return f'''import express from 'express';
import {{ config }} from './config';
import {{ healthRouter }} from './routes/health';

const app = express();

app.use(express.json());
app.use('/health', healthRouter);

app.get('/', (req, res) => {{
  res.json({{ message: 'Welcome to {config.name}' }});
}});

app.listen(config.port, () => {{
  console.log(`Server running on port ${{config.port}}`);
}});
'''

    def _typescript_config(self, config: ServiceConfig) -> str:
        return f'''import dotenv from 'dotenv';

dotenv.config();

export const config = {{
  port: parseInt(process.env.PORT || '{config.port}', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
}};
'''

    def _typescript_health_route(self, config: ServiceConfig) -> str:
        return '''import { Router } from 'express';

export const healthRouter = Router();

healthRouter.get('/', (req, res) => {
  res.json({ status: 'healthy' });
});

healthRouter.get('/ready', (req, res) => {
  res.json({ status: 'ready' });
});

healthRouter.get('/live', (req, res) => {
  res.json({ status: 'alive' });
});
'''

    def _typescript_dockerfile(self, config: ServiceConfig) -> str:
        return f'''FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-slim

WORKDIR /app

RUN adduser --disabled-password --gecos '' appuser

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

USER appuser

EXPOSE {config.port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD node -e "require('http').get('http://localhost:{config.port}/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "dist/index.js"]
'''

    # Go templates
    def _go_mod(self, config: ServiceConfig) -> str:
        return f'''module {config.name}

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
)
'''

    def _go_main(self, config: ServiceConfig) -> str:
        return f'''package main

import (
    "log"
    "{config.name}/internal/config"
    "{config.name}/internal/handlers"
    "github.com/gin-gonic/gin"
)

func main() {{
    cfg := config.Load()

    r := gin.Default()

    // Health routes
    r.GET("/health", handlers.HealthCheck)
    r.GET("/health/ready", handlers.ReadinessCheck)
    r.GET("/health/live", handlers.LivenessCheck)

    // Root route
    r.GET("/", func(c *gin.Context) {{
        c.JSON(200, gin.H{{"message": "Welcome to {config.name}"}})
    }})

    log.Printf("Starting server on port %d", cfg.Port)
    if err := r.Run(fmt.Sprintf(":%d", cfg.Port)); err != nil {{
        log.Fatal(err)
    }}
}}
'''

    def _go_config(self, config: ServiceConfig) -> str:
        return f'''package config

import (
    "os"
    "strconv"
)

type Config struct {{
    Port int
    Env  string
}}

func Load() *Config {{
    port := {config.port}
    if p := os.Getenv("PORT"); p != "" {{
        if parsed, err := strconv.Atoi(p); err == nil {{
            port = parsed
        }}
    }}

    return &Config{{
        Port: port,
        Env:  getEnv("ENV", "development"),
    }}
}}

func getEnv(key, defaultValue string) string {{
    if value := os.Getenv(key); value != "" {{
        return value
    }}
    return defaultValue
}}
'''

    def _go_health_handler(self, config: ServiceConfig) -> str:
        return '''package handlers

import (
    "github.com/gin-gonic/gin"
)

func HealthCheck(c *gin.Context) {
    c.JSON(200, gin.H{"status": "healthy"})
}

func ReadinessCheck(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ready"})
}

func LivenessCheck(c *gin.Context) {
    c.JSON(200, gin.H{"status": "alive"})
}
'''

    def _go_dockerfile(self, config: ServiceConfig) -> str:
        return f'''FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/server

FROM gcr.io/distroless/static-debian12

COPY --from=builder /app/server /server

EXPOSE {config.port}

USER nonroot:nonroot

ENTRYPOINT ["/server"]
'''

    # Common templates
    def _readme(self, config: ServiceConfig) -> str:
        return f'''# {config.name}

{config.description}

## Quick Start

### Prerequisites

- Docker
- Make (optional)

### Running locally

```bash
# Using Docker
docker compose up

# Or run directly
{"uvicorn app.main:app --reload" if config.language == Language.PYTHON else "npm run dev" if config.language == Language.TYPESCRIPT else "go run ./cmd/server"}
```

### Running tests

```bash
{"pytest" if config.language == Language.PYTHON else "npm test" if config.language == Language.TYPESCRIPT else "go test ./..."}
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

## Configuration

Configuration is done via environment variables. See `.env.example` for available options.

## License

MIT
'''

    def _gitignore(self, config: ServiceConfig) -> str:
        ignores = [
            "# Environment",
            ".env",
            ".env.local",
            "",
            "# IDE",
            ".idea/",
            ".vscode/",
            "*.swp",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
        ]

        if config.language == Language.PYTHON:
            ignores.extend([
                "",
                "# Python",
                "__pycache__/",
                "*.py[cod]",
                ".pytest_cache/",
                ".coverage",
                "htmlcov/",
                "dist/",
                "*.egg-info/",
                ".venv/",
                "venv/",
            ])
        elif config.language == Language.TYPESCRIPT:
            ignores.extend([
                "",
                "# Node",
                "node_modules/",
                "dist/",
                "coverage/",
                "*.log",
            ])
        elif config.language == Language.GO:
            ignores.extend([
                "",
                "# Go",
                "*.exe",
                "*.test",
                "*.out",
                "vendor/",
            ])

        return "\n".join(ignores) + "\n"

    def _env_example(self, config: ServiceConfig) -> str:
        env_vars = [
            f"PORT={config.port}",
            "ENV=development",
            "LOG_LEVEL=debug",
        ]
        env_vars.extend([f"{k}={v}" for k, v in config.env_vars.items()])
        return "\n".join(env_vars) + "\n"

    def _docker_compose(self, config: ServiceConfig) -> str:
        return f'''version: "3.8"

services:
  {config.name}:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "{config.port}:{config.port}"
    environment:
      - PORT={config.port}
      - ENV=development
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{config.port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
'''

    def _get_next_steps(self, config: ServiceConfig) -> List[str]:
        """Get next steps for the generated project."""
        steps = [
            f"cd {config.name}",
        ]

        if config.language == Language.PYTHON:
            steps.extend([
                "python -m venv .venv",
                "source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows",
                "pip install -r requirements.txt",
                "uvicorn app.main:app --reload",
            ])
        elif config.language == Language.TYPESCRIPT:
            steps.extend([
                "npm install",
                "npm run dev",
            ])
        elif config.language == Language.GO:
            steps.extend([
                "go mod tidy",
                "go run ./cmd/server",
            ])

        steps.append("Visit http://localhost:" + str(config.port))

        return steps

    def save_to_directory(
        self, report: ScaffoldReport, output_dir: Optional[str] = None
    ) -> str:
        """
        Save generated project to directory.

        Args:
            report: Scaffold report with files
            output_dir: Override output directory

        Returns:
            Path to the saved project
        """
        target_dir = output_dir or self.output_dir

        # Create directories
        for directory in report.directories:
            dir_path = os.path.join(target_dir, directory)
            os.makedirs(dir_path, exist_ok=True)

        # Create files
        for file_entry in report.files:
            file_path = os.path.join(target_dir, file_entry.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_entry.content)
            if file_entry.executable:
                os.chmod(file_path, 0o755)

        return os.path.join(target_dir, report.project_name)
