# AWS CLI/CDK Scripts

Minimal, copy-paste friendly commands per copilot-instructions.md.

Install CDK if missing:

```bash
npm install -g aws-cdk
```

Source the Python virtual environment (once per session):

```bash
source cdk_venv/bin/activate
```

Useful CDK helpers:

```bash
# From the CDK app directory (if applicable):
cd infrastructure/cdk

# Synthesize CloudFormation
cdk synth

# Show stack differences
cdk diff

# Bootstrap (first-time per account/region)
cdk bootstrap
```

Development (dev):

```bash
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

Production (prod):

```bash
cdk deploy \
  -c environment=prod \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```

Notes:
- Use the default AWS profile locally.
- Always test against AWS; never deploy to Railway.