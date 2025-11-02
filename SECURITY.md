# Security Guidelines

## MCP Configuration

The `.mcp.json` file contains sensitive credentials and should **never** be committed to version control.

### Setup Instructions

1. Copy the example file:
   ```bash
   cp .mcp.json.example .mcp.json
   ```

2. Update `.mcp.json` with your actual credentials:
   - Replace `YOUR_GITHUB_TOKEN_HERE` with your GitHub Personal Access Token
   - Update any paths specific to your system

3. The `.mcp.json` file is ignored by git and will not be committed.

### Creating GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select required scopes based on your needs
4. Copy the token and add it to your local `.mcp.json` file
5. **Never** share or commit this token

## Secrets Management

- All secrets should be stored in environment variables or secure credential stores
- Never hardcode secrets in source code
- Use AWS Secrets Manager or Parameter Store for production secrets
- Rotate credentials regularly

## Reporting Security Issues

If you discover a security vulnerability, please report it via:
- Email: security@vgnshlv.nz
- Create a private security advisory on GitHub

Do not create public issues for security vulnerabilities.
