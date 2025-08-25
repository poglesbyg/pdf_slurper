#!/bin/bash

# OpenShift Resource Quota Management Script
# Helps diagnose and resolve quota issues

echo "============================================"
echo "OpenShift Resource Quota Management"
echo "============================================"

# Check current namespace
NAMESPACE="${1:-pdf-slurper}"
echo "Namespace: $NAMESPACE"

# Try to get quota information
echo ""
echo "Checking resource quota..."
if oc get resourcequota -n "$NAMESPACE" 2>/dev/null; then
    echo "✓ Resource quota retrieved"
else
    echo "⚠ Cannot view resource quota (may need additional permissions)"
fi

# Check current pods and their resource usage
echo ""
echo "Current pods in namespace:"
if oc get pods -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,MEM_REQ:.spec.containers[0].resources.requests.memory,MEM_LIMIT:.spec.containers[0].resources.limits.memory,CPU_REQ:.spec.containers[0].resources.requests.cpu,CPU_LIMIT:.spec.containers[0].resources.limits.cpu 2>/dev/null; then
    echo ""
else
    echo "⚠ Cannot list pods (may need additional permissions)"
fi

# Check deployments
echo ""
echo "Current deployments:"
if oc get deployments -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas,MEM_LIMIT:.spec.template.spec.containers[0].resources.limits.memory,CPU_LIMIT:.spec.template.spec.containers[0].resources.limits.cpu 2>/dev/null; then
    echo ""
else
    echo "⚠ Cannot list deployments"
fi

# Options to free up resources
echo ""
echo "============================================"
echo "Options to resolve quota issues:"
echo "============================================"
echo ""
echo "1. Use MINIMAL deployment (64Mi memory limit):"
echo "   oc apply -f openshift/deployment-minimal.yaml"
echo ""
echo "2. Scale down existing deployments:"
echo "   oc scale deployment/<deployment-name> --replicas=0"
echo ""
echo "3. Delete unused pods:"
echo "   oc delete pod <pod-name>"
echo ""
echo "4. Delete all pods in Error or Completed state:"
echo "   oc delete pods --field-selector=status.phase=Failed"
echo "   oc delete pods --field-selector=status.phase=Succeeded"
echo ""
echo "5. Update deployment with reduced resources:"
echo "   oc set resources deployment/pdf-slurper-v2 --limits=memory=128Mi,cpu=200m --requests=memory=64Mi,cpu=50m"
echo ""
echo "6. Check what's using the most resources:"
echo "   oc adm top pods -n $NAMESPACE"
echo ""

# Quick fix option
echo "============================================"
echo "Quick Fix Commands:"
echo "============================================"
echo ""
echo "# Option A: Apply minimal deployment (recommended)"
echo "oc apply -f openshift/deployment-minimal.yaml"
echo ""
echo "# Option B: Patch existing deployment with minimal resources"
echo "oc patch deployment pdf-slurper-v2 -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"pdf-slurper\",\"resources\":{\"limits\":{\"memory\":\"128Mi\",\"cpu\":\"200m\"},\"requests\":{\"memory\":\"64Mi\",\"cpu\":\"50m\"}}}]}}}}'"
echo ""
echo "# Option C: Scale down and restart"
echo "oc scale deployment pdf-slurper-v2 --replicas=0"
echo "sleep 5"
echo "oc scale deployment pdf-slurper-v2 --replicas=1"
