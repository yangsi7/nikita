---
description: Perform security analysis on code using Gemini's code analyzer (focuses on vulnerabilities, injection attacks, hardcoded secrets)
allowed-tools:
  - mcp__gemini__gemini-analyze-code
  - Read
  - Grep
---

# Security Audit via Gemini

Perform comprehensive security analysis on the following code, focusing on:
- Hardcoded secrets (API keys, passwords, tokens)
- Injection vulnerabilities (SQL, command, XSS)
- Authentication/authorization issues
- Insecure cryptography
- OWASP Top 10 vulnerabilities

$ARGUMENTS
