# Django and Python Coding Standards

## Python Code Quality
- All Python code must use type hints for function parameters and return values
- Use Python 3.13+ features and syntax
- Follow PEP 8 style guidelines strictly
- Use dataclasses or Pydantic models for structured data when appropriate
- Avoid using `any` types in favor of specific type annotations

## Django Model Standards
- All models must inherit from `core.models.BaseModel` instead of `django.db.models.Model` to include audit trail fields (created_at, updated_at, created_by, modified_by, assigned_to)
- Model classes must include proper `__str__` methods that return meaningful string representations
- Use `CharField` with explicit `max_length` parameter, never rely on defaults
- Foreign key relationships must specify `on_delete` behavior explicitly
- Use `related_name` for foreign keys to avoid naming conflicts, especially in multi-tenant scenarios

## Django Admin Standards
- All model admin classes must inherit from `core.admin.BaseModelAdmin` to ensure consistent user tracking
- Admin classes must include `list_display`, `list_filter`, and `search_fields` where appropriate
- Use `readonly_fields` for audit trail fields (created_at, updated_at, created_by, modified_by)
- Include proper fieldsets for organized form layouts
- Register admin classes using the `@admin.register(Model)` decorator

## Import Organization
- Django imports first, then third-party packages, then local imports
- Use absolute imports for all project modules
- Group imports logically and separate with blank lines
- Avoid wildcard imports (`from module import *`)

## Code Documentation
- All classes and functions must include docstrings following Google or NumPy docstring format
- Complex business logic must be documented with inline comments
- Use meaningful variable and function names that are self-documenting