#!/bin/bash
# =============================================================================
# demo_aws_live.sh — optional, NOT required by the assessment.
#
# Part D's graded deliverable is the Lambda code + CloudFormation template —
# the assessment explicitly says deployment isn't required, and run_checks.sh
# (the actual required validation entry point) never touches AWS, by design.
#
# This script is a bonus: a narrated, step-by-step walkthrough of the stack
# actually running in a real AWS account, for live interview demonstration.
# Each step pauses so you can explain what just happened before moving on —
# the AWS equivalent of run_checks.sh, except AWS benefits from narration
# between steps rather than one silent pass/fail.
#
# Assumes the stack from infra/canary-stack.yaml is already deployed
# (see README.md §18). Set the three variables below to match your own
# deployment — nothing here is tied to any specific AWS account.
#
# Usage: chmod +x demo_aws_live.sh && ./demo_aws_live.sh
# =============================================================================

set -euo pipefail

STACK_NAME="${STACK_NAME:-qa-canary}"
FUNCTION_NAME="${FUNCTION_NAME:-qa-canary-canary}"
REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="QA/DummyJSON"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

section() {
  echo ""
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${YELLOW}  $1${NC}"
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

pause() {
  echo ""
  read -p "  ↳ Press Enter to continue... " _
}

# Looked up from the stack's own Outputs rather than hardcoded, so this
# script has no AWS-account-specific values baked in anywhere.
TOPIC_ARN=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='CanaryAlertTopicArn'].OutputValue" --output text)

# =============================================================================
section "Step 1 — The stack CloudFormation provisioned"
echo "Say: 'One template, nine resources, deployed consistently — no manual clicking.'"
echo ""
aws cloudformation describe-stack-resources --stack-name "$STACK_NAME" --region "$REGION" \
  --query 'StackResources[].{Type:ResourceType,Status:ResourceStatus,Id:LogicalResourceId}' --output table
pause

# =============================================================================
section "Step 2 — Confirm the schedule is disabled by design"
echo "Say: 'This doesn't run on a timer unless I deliberately enable it.'"
echo ""
aws scheduler get-schedule --name "${STACK_NAME}-schedule" --region "$REGION" \
  --query '{State:State,Expression:ScheduleExpression}'
pause

# =============================================================================
section "Step 3 — Invoke the Lambda live"
echo "Say: 'Let's actually run it — this calls the real DummyJSON API right now.'"
echo ""
aws lambda invoke --function-name "$FUNCTION_NAME" --payload '{}' --region "$REGION" /tmp/canary-response.json
echo ""
cat /tmp/canary-response.json | python3 -m json.tool
pause

# =============================================================================
section "Step 4 — The structured logs from that exact invocation"
echo "Say: 'One JSON line per check — Lambda ships stdout here automatically.'"
echo ""
START_MS=$(($(date +%s) * 1000 - 120000))
aws logs filter-log-events --log-group-name "/aws/lambda/${FUNCTION_NAME}" \
  --start-time "$START_MS" --region "$REGION" --query 'events[].message' --output text
pause

# =============================================================================
section "Step 5 — The metrics that invocation published"
echo "Say: 'Three metrics, one put_metric_data call — these are what the alarms watch.'"
echo ""
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%S)
START_TIME=$(date -u -v-10M +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S)
for METRIC in Availability ProductsLatencyMs AuthLatencyMs; do
  echo "--- $METRIC ---"
  aws cloudwatch get-metric-statistics --namespace "$NAMESPACE" --metric-name "$METRIC" \
    --start-time "$START_TIME" --end-time "$END_TIME" --period 60 --statistics Average \
    --region "$REGION" --query 'Datapoints[-1]'
done
pause

# =============================================================================
section "Step 6 — Alarm states"
echo "Say: 'Both alarms evaluate those metrics continuously — here's their current state.'"
echo ""
aws cloudwatch describe-alarms --alarm-names "${STACK_NAME}-AvailabilityAlarm" "${STACK_NAME}-LatencyAlarm" \
  --region "$REGION" --query 'MetricAlarms[].{Name:AlarmName,State:StateValue}' --output table
pause

# =============================================================================
section "Step 7 — SNS subscription, confirmed"
echo "Say: 'Both alarms point here — a real, confirmed email subscription, not just a config.'"
echo ""
aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --region "$REGION" \
  --query 'Subscriptions[].{Endpoint:Endpoint,SubscriptionArn:SubscriptionArn}' --output table
pause

# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Demo complete. Close with:${NC}"
echo -e "${GREEN}  'Everything here tears down with one command — I've verified that too.'${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "When you're actually ready to tear down (not during the live demo unless asked):"
echo "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"
echo "  aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION"
echo "  aws s3 rm s3://<your-build-bucket>/canary.zip"
echo "  aws s3 rb s3://<your-build-bucket>"
