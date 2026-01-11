# Railway PR Environments: Native vs Custom

## Overview

This project supports two approaches for creating ephemeral environments for pull requests:

1. **Railway Native PR Environments** (Recommended) - Platform-managed, zero-config
2. **Custom Ephemeral Environments** - Script-based, full control

This document helps you understand the differences and choose the right approach.

## Quick Comparison

| Aspect | Native PR Environments | Custom Ephemeral Environments |
|--------|----------------------|------------------------------|
| **Setup Time** | 5 minutes | 30+ minutes |
| **Configuration** | Railway Dashboard only | GitHub Actions + Scripts + Docs |
| **Maintenance** | Zero (managed by Railway) | Ongoing (scripts, workflows) |
| **GitHub Integration** | Built-in status checks | Custom implementation needed |
| **Lifecycle** | Fully automatic | Requires workflow triggers |
| **Reliability** | Very high (platform-managed) | Depends on custom code |
| **Customization** | Limited (inherits from base) | Full control |
| **Cost** | Same as custom | Same as native |
| **When to Use** | Standard PR workflows | Special cases, custom needs |

## Railway Native PR Environments

### What It Is

A built-in Railway platform feature that automatically creates, deploys, and destroys ephemeral environments for pull requests.

### How It Works

```
1. Enable in Railway Dashboard (one-time setup)
2. Open PR → Railway creates environment automatically
3. Push updates → Railway redeploys automatically
4. Close PR → Railway destroys environment automatically
```

### Pros

✅ **Zero Configuration** - Enable once, works forever  
✅ **Zero Maintenance** - Railway manages everything  
✅ **Native GitHub Integration** - Status checks, deployment links  
✅ **Reliable** - Platform-managed, tested by Railway  
✅ **Consistent** - Uses proven Railway deployment pipeline  
✅ **Simple** - No scripts, no workflows, no complexity  
✅ **Fast Setup** - 5 minutes from start to finish  

### Cons

❌ **Limited Customization** - Cannot change naming, lifecycle  
❌ **Fixed to PRs** - Only triggered by pull requests  
❌ **Less Control** - Cannot customize deployment logic  
❌ **Platform Dependent** - Requires Railway GitHub app access  

### Best For

- ✓ Standard pull request workflows
- ✓ Teams wanting minimal maintenance
- ✓ Projects with straightforward needs
- ✓ When Railway's defaults work for you
- ✓ Most projects (95% use case)

### Files

**Documentation:**
- `docs/RAILWAY_PR_ENVIRONMENTS_NATIVE.md` - Quick start guide
- `.github/skills/railway-service-management/reference/pr_environments.md` - Complete reference

**Workflows:**
- `.github/workflows/railway-pr-checks.yml` - Tests and validation (optional)

**Setup:**
- Railway Dashboard → Settings → GitHub → PR Environments

## Custom Ephemeral Environments

### What It Is

A custom implementation using GitHub Actions workflows and bash scripts to create and manage ephemeral Railway environments.

### How It Works

```
1. GitHub Actions workflow triggers on PR events
2. Custom script creates Railway environment
3. Custom script configures environment variables
4. Custom script deploys application
5. Custom script tests deployment
6. Custom script destroys environment on PR close
```

### Pros

✅ **Full Control** - Customize every aspect of lifecycle  
✅ **Flexible Naming** - Use any naming convention  
✅ **Non-PR Triggers** - Support Copilot sessions, manual deploys  
✅ **Custom Logic** - Add complex deployment strategies  
✅ **Advanced Features** - Pre/post deployment hooks  
✅ **Workarounds** - Can work around platform limitations  

### Cons

❌ **Complex Setup** - Multiple files, workflows, scripts  
❌ **Ongoing Maintenance** - Scripts need updates, debugging  
❌ **Custom Integration** - Must implement GitHub status checks  
❌ **Potential Bugs** - Custom code can have issues  
❌ **Higher Learning Curve** - Team needs to understand custom code  
❌ **More Moving Parts** - More things that can break  

### Best For

- ✓ Custom environment naming requirements
- ✓ Non-PR deployments (Copilot sessions, manual)
- ✓ Advanced deployment strategies
- ✓ Working around platform limitations
- ✓ When you need full control
- ✓ Special use cases (5% use case)

### Files

**Scripts:**
- `scripts/railway_ephemeral_env.sh` - Environment lifecycle management

**Workflows:**
- `.github/workflows/railway-pr-environments.yml` - PR environment automation (disabled)
- `.github/workflows/railway-copilot-environments.yml` - Copilot session environments

**Documentation:**
- `docs/EPHEMERAL_RAILWAY_ENVIRONMENTS.md` - Complete guide
- `docs/EPHEMERAL_ENVIRONMENTS_QUICK_REF.md` - Quick reference

## Decision Matrix

### Choose Native PR Environments If:

- ✅ You're setting up PR environments for the first time
- ✅ Standard PR workflow meets your needs
- ✅ You want minimal maintenance
- ✅ You trust Railway's automation
- ✅ You don't need custom environment names
- ✅ PRs are your only trigger
- ✅ You want the simplest solution

### Choose Custom Ephemeral Environments If:

- ✅ You need custom environment naming (not pr-{number})
- ✅ You need to trigger deployments outside of PRs
- ✅ You need advanced pre/post deployment logic
- ✅ You're working around specific platform limitations
- ✅ You have unique compliance requirements
- ✅ You need full control over every step
- ✅ You have DevOps resources for maintenance

### Use Both (Hybrid Approach) If:

- ✅ Standard PRs use native environments (most common case)
- ✅ Special cases use custom scripts (Copilot sessions, etc.)
- ✅ You want best of both worlds
- ✅ You need flexibility without sacrificing simplicity

## Current Status in This Project

### What's Enabled

✅ **Railway Native PR Environments** - Active and recommended  
✅ **Custom Scripts** - Available for special cases  
✅ **Testing Workflow** - `railway-pr-checks.yml` for validation  

### What's Disabled

⚠️ **Custom PR Workflow** - `.github/workflows/railway-pr-environments.yml` (disabled)  
   - Reason: Replaced by Railway native feature
   - Status: Kept for reference and special cases

### Recommended Approach

**For Pull Requests:**
```
Use Railway Native PR Environments (automatic, zero-config)
```

**For Copilot Sessions:**
```bash
Use Custom Scripts:
./scripts/railway_ephemeral_env.sh deploy copilot-my-session
```

**For Testing:**
```
Use GitHub Actions workflow: railway-pr-checks.yml (optional)
```

## Migration Guide

### From Custom to Native

**Step 1: Enable Native PR Environments**
```
Railway Dashboard → Settings → GitHub → PR Environments → Enable
```

**Step 2: Disable Custom Workflow**
```yaml
# .github/workflows/railway-pr-environments.yml
# Already disabled in this project
```

**Step 3: Test**
```
Open a test PR and verify Railway creates environment automatically
```

**Step 4: Document**
```
Update team documentation to reference native approach
```

### Keeping Both (Hybrid)

**For PRs:** Railway handles automatically (native)  
**For Other:** Use custom scripts as needed

This is the **current setup** in this project.

## Cost Comparison

Both approaches have **identical costs**:

- Same infrastructure (Railway environments)
- Same resources (web service, database)
- Same pricing model
- Same auto-cleanup

**Per Environment:**
- ~$0.01-0.03/hour
- Average PR: $0.03-0.12
- No difference in cost between native and custom

## Feature Comparison Details

### Deployment Trigger

**Native:**
- ✓ Pull request opened
- ✓ Pull request synchronized (new commits)
- ✓ Pull request reopened
- ❌ Manual trigger
- ❌ Custom triggers

**Custom:**
- ✓ Pull request events
- ✓ Manual trigger (workflow_dispatch)
- ✓ Branch push events
- ✓ Scheduled triggers
- ✓ Any custom trigger

### Environment Naming

**Native:**
- Fixed pattern: `pr-{number}`
- Examples: `pr-123`, `pr-456`
- Cannot customize

**Custom:**
- Any pattern: `pr-{number}`, `copilot-{name}`, `test-{id}`
- Examples: `pr-123`, `copilot-add-auth`, `test-feature-x`
- Fully customizable

### Lifecycle Management

**Native:**
- Automatic creation on PR open
- Automatic deployment on PR update
- Automatic destruction on PR close/merge
- No manual intervention needed

**Custom:**
- Manual script execution (or workflow-triggered)
- Custom deployment logic
- Custom cleanup logic
- Requires monitoring and maintenance

### GitHub Integration

**Native:**
- Built-in status checks
- Deployment links in PR
- GitHub Environments integration
- Automatic status updates

**Custom:**
- Must implement status checks
- Must post PR comments
- Must create GitHub Environments
- Manual integration required

### Configuration

**Native:**
- Inherits from base environment (staging)
- Limited customization
- Railway Dashboard configuration

**Custom:**
- Full control over variables
- Custom configuration per environment
- Script-based configuration

## Troubleshooting

### When Native Doesn't Work

**Issue:** Need custom environment names  
**Solution:** Use custom scripts for those specific cases

**Issue:** Need non-PR triggers  
**Solution:** Use custom scripts with workflow_dispatch

**Issue:** Need advanced deployment logic  
**Solution:** Use custom scripts with pre/post hooks

### When Custom Is Too Complex

**Issue:** Too much maintenance  
**Solution:** Migrate to Railway native for standard PRs

**Issue:** Scripts breaking frequently  
**Solution:** Simplify to Railway native, keep scripts for edge cases

**Issue:** Team confusion  
**Solution:** Use Railway native (simpler), document exceptions

## Best Practices

### For Native PR Environments

1. ✓ Enable for all target branches (main, develop)
2. ✓ Use staging as base template
3. ✓ Set appropriate resource limits
4. ✓ Monitor deployment status
5. ✓ Close PRs promptly
6. ✓ Document testing procedures
7. ✓ Add GitHub Actions for validation (optional)

### For Custom Ephemeral Environments

1. ✓ Maintain scripts regularly
2. ✓ Document custom logic clearly
3. ✓ Test scripts before deploying
4. ✓ Monitor for failures
5. ✓ Have rollback procedures
6. ✓ Use for special cases only
7. ✓ Consider migrating to native when possible

### For Hybrid Approach (Recommended)

1. ✓ Use native for standard PRs (95% of cases)
2. ✓ Keep custom scripts for special needs (5%)
3. ✓ Document when to use each approach
4. ✓ Train team on both methods
5. ✓ Regularly review and simplify

## Summary

### Recommendations

**For Most Projects:**
```
Use Railway Native PR Environments
- Simple, reliable, zero maintenance
- Perfect for 95% of use cases
```

**For Complex Needs:**
```
Use Hybrid Approach (like this project)
- Native for standard PRs
- Custom for special cases
```

**Rarely Needed:**
```
Custom-Only Approach
- Only if platform limitations are blockers
- Requires ongoing maintenance commitment
```

### This Project's Approach

✅ **Railway Native PR Environments** - Primary method for PRs  
✅ **Custom Scripts** - Available for Copilot sessions and special cases  
✅ **Testing Workflow** - Optional GitHub Actions for validation  
📚 **Complete Documentation** - Both approaches documented  

**Result:** Best of both worlds - simplicity for common cases, flexibility for special needs.

---

**See Also:**
- [Native PR Environments Guide](./RAILWAY_PR_ENVIRONMENTS_NATIVE.md)
- [Custom Ephemeral Environments Guide](./EPHEMERAL_RAILWAY_ENVIRONMENTS.md)
- [Skill Reference](./.github/skills/railway-service-management/reference/pr_environments.md)
