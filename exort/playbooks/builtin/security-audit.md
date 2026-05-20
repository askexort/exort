# Security Audit Checklist

## Authentication
- [ ] Passwords hashed (bcrypt/argon2, not MD5/SHA1)
- [ ] Rate limiting on login
- [ ] MFA available
- [ ] Session timeout configured
- [ ] JWT tokens expire

## Authorization
- [ ] RBAC implemented
- [ ] Users can only access own data
- [ ] Admin endpoints protected
- [ ] API keys rotated regularly

## Input Validation
- [ ] All user input sanitized
- [ ] SQL parameterized (no string concat)
- [ ] XSS prevention (output encoding)
- [ ] File upload restrictions
- [ ] Request size limits

## Secrets
- [ ] No secrets in code
- [ ] .env in .gitignore
- [ ] API keys in environment variables
- [ ] Credentials rotated periodically

## Infrastructure
- [ ] HTTPS everywhere
- [ ] Security headers set
- [ ] Dependencies updated
- [ ] Logs don't contain secrets
- [ ] Error messages don't leak internals
