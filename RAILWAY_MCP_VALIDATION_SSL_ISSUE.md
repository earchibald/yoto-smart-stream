# Railway MCP Validation - SSL Certificate Issue Addendum

## Date
2026-01-11 (Update after domain allowlist addition)

## Status
❌ **Validation Blocked by SSL Certificate Trust Issue**

## Context

After the user added `railway.com` to the Copilot Workspace allowlist, a new issue was discovered that prevents Railway CLI operation in the Copilot Workspace environment.

## The Problem

### DNS Resolution: ✅ WORKING
The domain `backboard.railway.com` now resolves correctly:
```bash
$ getent hosts backboard.railway.com
104.18.25.53    backboard.railway.com
104.18.24.53    backboard.railway.com
```

### HTTP/HTTPS Access: ✅ WORKING (for curl)
```bash
$ curl -s -o /dev/null -w "%{http_code}" https://backboard.railway.com/graphql/v2
400  # Expected - GraphQL endpoint requires POST with proper data
```

### Railway CLI: ❌ BLOCKED
```bash
$ railway whoami
Failed to fetch: error sending request for url (https://backboard.railway.com/graphql/v2)

Caused by:
    0: error sending request for url (https://backboard.railway.com/graphql/v2)
    1: client error (Connect)
    2: invalid peer certificate: UnknownIssuer
```

## Root Cause Analysis

### MITM Proxy Certificate Interception

The Copilot Workspace firewall uses a Man-In-The-Middle (MITM) proxy to enforce domain allowlists. This proxy:

1. **Intercepts HTTPS connections** to check if domains are allowed
2. **Presents its own certificate** signed by a local CA (`mkcert development CA`)
3. **Re-encrypts the connection** to the actual destination

**Certificate Chain Observed:**
```
issuer=O = mkcert development CA, OU = runner@runnervmi13qx, CN = mkcert runner@runnervmi13qx
subject=O = GoProxy untrusted MITM proxy Inc, CN = backboard.railway.com
```

### Railway CLI Certificate Validation

The Railway CLI is a Rust-based binary that uses strict TLS certificate validation:

- **Library**: Likely uses `reqwest` or `hyper` with `rustls` or `native-tls`
- **Behavior**: Does not trust the MITM proxy's certificate
- **Error**: "invalid peer certificate: UnknownIssuer"

### Why curl Works But Railway CLI Doesn't

| Tool | Certificate Validation | System CA Store | Result |
|------|----------------------|-----------------|--------|
| curl | Uses OpenSSL | ✅ Uses system store | ✅ Works |
| Railway CLI (Rust) | Built-in TLS validation | ❌ Does not use system store | ❌ Fails |

## Attempted Solutions

### 1. ✅ Added Domain to Allowlist (User Action)
- **Status**: Completed by user
- **Result**: DNS resolution works, but SSL validation still fails

### 2. ✅ Extracted MITM CA Certificate
```bash
$ openssl s_client -connect backboard.railway.com:443 -showcerts
# Extracted mkcert development CA certificate
```

### 3. ✅ Added CA to System Trust Store
```bash
$ sudo cp copilot-root-ca.crt /usr/local/share/ca-certificates/
$ sudo update-ca-certificates
Updating certificates in /etc/ssl/certs...
1 added, 0 removed; done.
```

### 4. ❌ Railway CLI Still Doesn't Trust It
The Railway CLI doesn't use the system CA trust store. Tested:
- `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` - ❌ No effect
- `SSL_CERT_DIR=/etc/ssl/certs` - ❌ No effect
- System update-ca-certificates - ❌ No effect

### 5. ❌ No CLI Options for Custom CAs
```bash
$ railway --help | grep -i cert
# No certificate-related options found
```

## Technical Limitations

### Railway CLI v4.23.0 Constraints
1. **No SSL bypass options** - Cannot disable certificate validation
2. **No custom CA support** - Cannot specify additional trusted CAs
3. **Hardcoded validation** - Uses built-in Rust TLS validation
4. **No environment variable override** - Doesn't respect SSL_CERT_* variables

### Rust TLS Behavior
Rust's TLS libraries (rustls, native-tls) use their own certificate validation:
- `rustls`: Uses embedded root CAs (webpki-roots)
- `native-tls`: May use platform-specific APIs, but in this case still rejects the cert

## Impact

### ❌ Blocked Operations
- **Railway CLI**: All commands fail with SSL error
- **Railway MCP Server**: All tools fail (uses CLI under the hood)
- **Validation Tasks**: Cannot complete original validation objectives

### ✅ Working Alternatives
- **curl**: Can access Railway APIs directly
- **Direct HTTP**: Raw HTTP requests work via curl/wget
- **Web Browser**: Would work if Railway had web UI operations

## Possible Workarounds (Not Implemented)

### Option 1: Modify Railway CLI Binary
- **Risk**: High - Binary modification
- **Difficulty**: High - Requires reverse engineering
- **Maintainability**: Poor - Would break on updates

### Option 2: Custom Proxy with Certificate Pinning Bypass
- **Risk**: High - Security implications
- **Difficulty**: High - Requires custom proxy implementation
- **Maintainability**: Poor - Complex setup

### Option 3: Use Railway API Directly via HTTP
- **Risk**: Low - Standard HTTP requests
- **Difficulty**: Medium - Need to implement Railway API calls
- **Maintainability**: Medium - Must keep up with API changes
- **Note**: This would bypass the Railway CLI entirely

### Option 4: Request Railway CLI Enhancement
- **Risk**: Low - Official feature request
- **Difficulty**: Low - Just request it
- **Maintainability**: High - Would be officially supported
- **Timeline**: Unknown - Depends on Railway team

## Recommendations

### For This Validation Task

1. **Document the Limitation**
   - ✅ Already done in this document
   - Update validation reports with SSL issue details
   - Mark validation as "Blocked by Technical Limitation"

2. **Alternative Validation Approach**
   - Consider validating Railway API access via curl
   - Test Railway GraphQL queries manually
   - Document that Railway CLI is blocked in this environment

3. **Update PR Description**
   - Explain the SSL certificate validation issue
   - Note that validation cannot be completed in current Copilot Workspace
   - Suggest alternative validation environments

### For Future Work

1. **Request Railway CLI Enhancement**
   - Open issue with Railway team
   - Request SSL certificate customization options
   - Reference this use case (CI/CD with MITM proxies)

2. **Alternative Deployment Tool**
   - Consider using Railway API directly via HTTP
   - Build custom deployment scripts if CLI remains blocked
   - Use Railway web UI for manual operations

3. **Test in Different Environment**
   - GitHub Codespaces (may have different firewall behavior)
   - Local development (no MITM proxy)
   - GitHub Actions (direct Railway API access)

## Conclusion

The Railway MCP tool validation cannot be completed in the GitHub Copilot Workspace environment due to:

1. ✅ Domain allowlist issue - **RESOLVED** (user added railway.com)
2. ❌ SSL certificate trust issue - **BLOCKED** (Railway CLI limitation)

**Root Cause**: Railway CLI uses strict TLS validation that doesn't trust MITM proxy certificates

**Blocker**: No options in Railway CLI to customize certificate validation

**Status**: Validation tasks cannot be completed until:
- Railway CLI adds custom CA support, OR
- Copilot Workspace removes MITM proxy for Railway domains, OR
- Alternative validation method is used (direct API calls)

**Recommendation**: Mark this validation as "Partially Complete" with detailed technical explanation of the blocker.

---

**Files Modified in This Investigation**:
- RAILWAY_MCP_VALIDATION_SSL_ISSUE.md (this document)
- RAILWAY_MCP_VALIDATION.md (to be updated with reference to this addendum)

**Next Steps**:
1. Update main validation report with SSL issue reference
2. Reply to user explaining the technical limitation
3. Suggest alternative validation approaches
4. Close validation task with explanation
