"""
Linter configuration templates for GAIA projects.

Contains the canonical linting configurations derived from GAIA coding standards.
These templates are used by the LinterInitializer to generate config files.
"""

# -- Python: Ruff configuration (appended to pyproject.toml) --

RUFF_PYPROJECT_TOML = """\

[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (import sorting)
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "SIM108", # use ternary operator (can reduce readability)
]

[tool.ruff.lint.isort]
known-first-party = ["{project_name}"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
"""

# -- Python: MyPy configuration (appended to pyproject.toml) --

MYPY_PYPROJECT_TOML = """\

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
check_untyped_defs = true
ignore_missing_imports = true
"""

# -- Python: pytest configuration (appended to pyproject.toml) --

PYTEST_PYPROJECT_TOML = """\

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
"""

# -- Python: Coverage configuration (appended to pyproject.toml) --

COVERAGE_PYPROJECT_TOML = """\

[tool.coverage.run]
source = ["{project_name}"]
omit = [
    "tests/*",
    "*/test_*",
    "*/__pycache__/*",
]

[tool.coverage.report]
show_missing = true
precision = 2
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
    "raise NotImplementedError",
]
"""

# -- Pre-commit configuration --

PRE_COMMIT_CONFIG = """\
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.0.0
          - pyyaml>=6.0
        args: ["--ignore-missing-imports"]
        pass_filenames: false
        entry: mypy {project_name}/
"""

# -- TypeScript/JavaScript: ESLint flat config --

ESLINT_CONFIG_JS = """\
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: {
      react,
      "react-hooks": reactHooks,
    },
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/explicit-function-return-type": "warn",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
  {
    ignores: ["node_modules/", "dist/", "build/", "coverage/"],
  }
);
"""

# -- TypeScript: tsconfig.json --

TSCONFIG_JSON = """\
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "declaration": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist", "build", "coverage"]
}
"""

# -- Prettier configuration --

PRETTIERRC_JSON = """\
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "avoid",
  "endOfLine": "auto"
}
"""

# -- Standalone ruff.toml (for projects that don't use pyproject.toml) --

RUFF_TOML = """\
target-version = "py311"
line-length = 120

[lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (import sorting)
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "SIM108", # use ternary operator (can reduce readability)
]

[lint.isort]
known-first-party = ["{project_name}"]

[format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
"""

# Map of template names to their content and target filenames
PYTHON_TEMPLATES = {
    "ruff": {
        "content": RUFF_PYPROJECT_TOML,
        "filename": "pyproject.toml",
        "mode": "append",
        "standalone_content": RUFF_TOML,
        "standalone_filename": "ruff.toml",
    },
    "mypy": {
        "content": MYPY_PYPROJECT_TOML,
        "filename": "pyproject.toml",
        "mode": "append",
    },
    "pytest": {
        "content": PYTEST_PYPROJECT_TOML,
        "filename": "pyproject.toml",
        "mode": "append",
    },
    "coverage": {
        "content": COVERAGE_PYPROJECT_TOML,
        "filename": "pyproject.toml",
        "mode": "append",
    },
    "pre-commit": {
        "content": PRE_COMMIT_CONFIG,
        "filename": ".pre-commit-config.yaml",
        "mode": "create",
    },
}

TYPESCRIPT_TEMPLATES = {
    "eslint": {
        "content": ESLINT_CONFIG_JS,
        "filename": "eslint.config.js",
        "mode": "create",
    },
    "tsconfig": {
        "content": TSCONFIG_JSON,
        "filename": "tsconfig.json",
        "mode": "create",
    },
    "prettier": {
        "content": PRETTIERRC_JSON,
        "filename": ".prettierrc",
        "mode": "create",
    },
}

# -- VSCode settings for Python projects --

VSCODE_SETTINGS_PYTHON = {
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit",
        },
    },
    "ruff.lint.run": "onSave",
    "mypy-type-checker.args": ["--ignore-missing-imports"],
    "python.analysis.typeCheckingMode": "basic",
}

# -- VSCode settings for TypeScript projects --

VSCODE_SETTINGS_TYPESCRIPT = {
    "[typescript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.fixAll.eslint": "explicit",
        },
    },
    "[typescriptreact]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {
            "source.fixAll.eslint": "explicit",
        },
    },
    "[javascript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode",
        "editor.formatOnSave": True,
    },
    "eslint.useFlatConfig": True,
}

# -- VSCode extension recommendations --

VSCODE_EXTENSIONS_PYTHON = [
    "charliermarsh.ruff",
    "ms-python.python",
    "ms-python.mypy-type-checker",
]

VSCODE_EXTENSIONS_TYPESCRIPT = [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
]

# -- CLI tool requirements --

PYTHON_TOOL_REQUIREMENTS = [
    {
        "command": "ruff",
        "check_args": ["--version"],
        "name": "Ruff",
        "install": "pip install ruff",
        "purpose": "Python linter and formatter",
    },
    {
        "command": "mypy",
        "check_args": ["--version"],
        "name": "MyPy",
        "install": "pip install mypy",
        "purpose": "Python type checker",
    },
    {
        "command": "pre-commit",
        "check_args": ["--version"],
        "name": "pre-commit",
        "install": "pip install pre-commit",
        "purpose": "Git hook manager (run 'pre-commit install' after installing)",
    },
]

TYPESCRIPT_TOOL_REQUIREMENTS = [
    {
        "command": "npx",
        "check_args": ["--version"],
        "name": "npx (Node.js)",
        "install": "Install Node.js from https://nodejs.org/ (LTS recommended)",
        "purpose": "Node.js package runner (required for ESLint and Prettier)",
    },
]

TYPESCRIPT_NPM_REQUIREMENTS = [
    {
        "package": "eslint",
        "name": "ESLint",
        "install": "npm install -D eslint @eslint/js typescript-eslint eslint-plugin-react eslint-plugin-react-hooks",
        "purpose": "TypeScript/JavaScript linter",
    },
    {
        "package": "prettier",
        "name": "Prettier",
        "install": "npm install -D prettier",
        "purpose": "Code formatter",
    },
    {
        "package": "typescript",
        "name": "TypeScript",
        "install": "npm install -D typescript",
        "purpose": "TypeScript compiler",
    },
]
