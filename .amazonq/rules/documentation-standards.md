# Documentation Standards for Taruvi Cloud Platform

## End-User Focused Documentation
- All documentation in the `docs/` folder is intended for end-users of the Taruvi Cloud platform, not internal developers
- Focus on how users can utilize Taruvi Cloud features, APIs, and services rather than internal code implementation details
- Document user-facing functionality, configuration options, and integration patterns
- Avoid exposing internal architecture details, database schemas, or Django-specific implementation
- Write from the perspective of someone using Taruvi Cloud as a service, not someone developing it

## Automatic Documentation Updates
- When creating or modifying user-facing features in pull requests, automatically review and update relevant documentation in the `docs/` folder
- Check existing documentation files to identify sections that need updates based on feature changes
- Create new documentation files when introducing new user-facing features, APIs, or services
- Update API documentation in `docs/docs/api/` when public REST endpoints are added, modified, or removed
- Focus on documenting the user experience and capabilities, not the internal implementation
- Ensure documentation changes are included in the same PR as user-facing feature changes

## MDX File Standards
- All documentation files must use `.mdx` extension to support React components and interactive elements
- Use proper frontmatter metadata at the top of each file:
  ```yaml
  ---
  title: Page Title
  description: Brief description of the content
  sidebar_position: 1
  tags: [tag1, tag2]
  ---
  ```
- Import and use Docusaurus components when appropriate (`Tabs`, `TabItem`, `Admonition`, `CodeBlock`)
- Include interactive code examples using CodeBlock with syntax highlighting

## Content Structure Requirements
- Start each document with a brief overview or introduction
- Use clear, descriptive headings that create a logical hierarchy
- Include code examples with proper syntax highlighting and language specification
- Add step-by-step procedures for complex setup or configuration tasks
- Include troubleshooting sections for common issues
- End with "Next Steps" or "Related Topics" sections when appropriate

## API Documentation Standards
- Document all public REST API endpoints that users can access:
  - HTTP method and URL pattern
  - Request parameters and body schema
  - Response format and status codes
  - Authentication requirements (API keys, tokens, etc.)
  - Example requests and responses using actual curl commands or code snippets
- Update API documentation when user-facing endpoints are added, modified, or removed
- Include rate limiting information and error handling examples
- Focus on how users can integrate with Taruvi Cloud APIs, not internal API structure

## Platform Documentation
- Document Taruvi Cloud platform capabilities and features from a user perspective
- Include setup guides for integrating with Taruvi Cloud services
- Provide configuration examples for common use cases
- Document authentication and authorization flows for end users
- Include troubleshooting guides for common user issues
- Avoid exposing internal system architecture or implementation details

## Code Example Standards
- All code examples must be functional and from a user integration perspective
- Use realistic example data that represents typical Taruvi Cloud usage scenarios
- Include both success and error handling examples for API integrations
- Provide copy-paste ready configuration snippets for common integrations
- Show examples in multiple programming languages where appropriate (curl, JavaScript, Python, etc.)
- Focus on client-side integration code, not server-side Django implementation

## Documentation Review Process
- Review existing documentation for accuracy before adding new content
- Check for outdated information and update or remove deprecated content
- Ensure cross-references and internal links remain valid
- Update table of contents and navigation when adding new sections
- Validate that all code examples work with current codebase version

## Writing Style Guidelines
- Use clear, concise language appropriate for technical documentation
- Write in active voice and use second person ("you") for instructions
- Define technical terms and acronyms on first use
- Use consistent terminology throughout all documentation
- Include accessibility considerations for code examples and UI instructions

## Maintenance and Organization
- Keep documentation structure aligned with actual codebase organization
- Archive or remove documentation for deprecated features
- Ensure sidebar navigation reflects current feature priorities
- Tag documentation appropriately for easy discovery
- Update the main README.md when major documentation changes occur