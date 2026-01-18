---
name: railway-service-management
description: Specialized knowledge for managing multi-environment Railway deployments, including development branch previews, production services, and full lifecycle management. Use this when setting up Railway infrastructure, configuring multi-environment workflows, or managing Railway deployments.
---

# Railway CLI Guidance
**ALWAYS** apply this guidance to **EVERY** use of the railway CLI.
- 

# Railway CLI Commands for common tasks

## Get Railway Status (Detailed, JSON)
`railway status --json`

## Get Railway Logs (Detailed, JSON)
### Deployment and Build logs options
```
  -d, --deployment                 Show deployment logs
  -b, --build                      Show build logs
```

### Apply Filtering (can be combined with --latest, --since or --lines)
Railway supports custom filter syntax for querying logs:
- **PREFER** to filter whenever possible for agent efficiency but widen search as needed

#### Filter Syntax:
- `"<search term>"` - Filter for partial substring match
- `@attribute:value` - Filter by custom attribute
- `@level:error` - Filter by error level
- `@level:warn` - Filter by warning level
- `@level:info` - Filter by info level
- `@level:debug` - Filter by debug level
- Combine with `AND`, `OR`, `-` (NOT)

#### Common Examples:
```bash
# Find logs with error level
railway logs --filter "@level:error"

# Find error logs containing specific text
railway logs --filter "@level:error AND \"failed to connect\""

# Find logs containing a substring
railway logs --filter "\"POST /api\""

# Exclude specific level
railway logs --filter "-@level:debug"
```

### **Stream** latest deployment logs (even if failed/building)
`railway logs --latest --json`
- After the desired timeout, send `^C` to exit

### By Time
`railway logs --since "$DURATION_GDATE_SYNTAX" --json`

### By Number of Lines
`railway logs --lines $NUM_LINES --json`
