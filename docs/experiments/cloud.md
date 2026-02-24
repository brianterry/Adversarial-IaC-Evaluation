# Cloud Deployment

Deploy infrastructure for large-scale experiments.

## AWS CDK Deployment

```bash
cd infrastructure/cdk
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

## Resources Created

- S3 bucket for results
- Lambda functions
- Step Functions workflow
- CloudWatch dashboard
