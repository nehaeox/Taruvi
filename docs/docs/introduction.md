# Introduction to Taruvi

Taruvi is a **multi-tenant Software-as-a-Service (SaaS) platform** built with Django 5.2.6, designed for enterprise-grade applications. It provides a robust foundation for building scalable SaaS products with isolated tenant data, shared infrastructure, and modern development practices.

## What is Taruvi?

Taruvi allows organizations to create isolated projects/sites with their own users, data, and configurations, while maintaining shared infrastructure and centralized administration. Each tenant (organization) gets their own database schema, ensuring complete data isolation while sharing common platform services.

## Key Features

### 🏗️ Multi-Tenant Architecture
- **Schema-based isolation** using django-tenants
- Shared platform infrastructure with isolated tenant data
- Automatic schema creation and management
- Dynamic subdomain routing (tenant.domain.com)

### 🔒 Enterprise Security
- JWT token authentication with refresh and blacklist
- Rate limiting and burst protection
- Comprehensive audit trails with django-simple-history
- Security headers and OWASP compliance
- Object-level permissions with django-guardian

### ⚡ Modern Tech Stack
- **Backend**: Django 5.2.6, Python 3.13
- **Database**: PostgreSQL with tenant schemas
- **API**: Django REST Framework with OpenAPI docs
- **Background Tasks**: Celery with SQS/Redis
- **Storage**: AWS S3 with CloudFront CDN
- **Admin**: Jazzmin-themed Django admin

### 🚀 Production-Ready
- Docker containerization with multi-stage builds
- Health checks and monitoring endpoints
- Structured JSON logging with correlation IDs
- OpenTelemetry tracing support
- Comprehensive error handling and validation

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                Platform Level                       │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │   Django Admin  │  │   API Gateway   │          │
│  │   (Shared)      │  │   (DRF + JWT)   │          │
│  └─────────────────┘  └─────────────────┘          │
│                                                     │
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │     Celery      │  │   Monitoring    │          │
│  │   (SQS + DB)    │  │  (Health/Logs)  │          │
│  └─────────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────┘
                         │
                         │ Multi-Tenant Layer
                         ▼
┌─────────────────────────────────────────────────────┐
│                Project Level                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  Project A  │  │  Project B  │  │  Project C  │ │
│  │ (Schema A)  │  │ (Schema B)  │  │ (Schema C)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Use Cases

Taruvi is perfect for:

- **SaaS Applications**: Build multi-tenant SaaS products with isolated customer data
- **Enterprise Platforms**: Create internal tools with department-level isolation
- **Client Portals**: Develop client-facing applications with secure data separation
- **Project Management**: Build platforms where teams work on isolated projects
- **White-label Solutions**: Create customizable platforms for different brands

## Getting Started

Ready to start building with Taruvi? Check out our [Getting Started Guide](./getting-started.md) to set up your development environment and create your first tenant.

## Core Concepts

Before diving in, familiarize yourself with these key concepts:

- **Tenants**: Organizations that use your platform (each gets isolated data)
- **Shared Schema**: Platform-wide data like tenant management and admin users
- **Tenant Schema**: Isolated data specific to each organization/project
- **Organizations**: Business entities that can have multiple sites/projects
- **Sites**: Individual projects or applications within an organization

## Community & Support

- **Documentation**: Comprehensive guides and API references
- **GitHub**: Source code, issues, and feature requests
- **Security**: Responsible disclosure and security best practices

Continue reading to learn how to [get started](./getting-started.md) with Taruvi or explore our [API documentation](./api/overview.md).