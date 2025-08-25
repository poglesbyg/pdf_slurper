#!/bin/bash

# Build and deploy the Web UI container to OpenShift

set -e

echo "============================================"
echo "Building PDF Slurper Web UI Container"
echo "============================================"

# Check if logged in to OpenShift
if ! oc whoami &> /dev/null; then
    echo "❌ Not logged in to OpenShift. Please run: oc login <server>"
    exit 1
fi

echo "✓ Logged in as: $(oc whoami)"

# Set namespace
NAMESPACE="${1:-pdf-slurper}"
echo "Using namespace: $NAMESPACE"
oc project "$NAMESPACE" || exit 1

# Build the Web UI image
echo ""
echo "Building Web UI image..."

# Start build from current directory
oc start-build pdf-slurper-web --from-dir=.. --follow || {
    echo "Build config doesn't exist. Creating it..."
    oc new-build --name=pdf-slurper-web \
        --binary \
        --strategy=docker \
        --docker-image=nginx:alpine-slim
    
    echo "Starting build..."
    oc start-build pdf-slurper-web --from-dir=.. --follow
}

echo ""
echo "✅ Web UI image built successfully!"

# Check if deployment exists
if oc get deployment pdf-slurper-web &> /dev/null; then
    echo "Rolling out new deployment..."
    oc rollout latest deployment/pdf-slurper-web
    oc rollout status deployment/pdf-slurper-web --timeout=300s
else
    echo "Creating web deployment..."
    oc apply -f ../openshift/deployment-combined.yaml
fi

echo ""
echo "============================================"
echo "✅ Web UI Build Complete!"
echo "============================================"

# Get route URL
ROUTE_URL=$(oc get route pdf-slurper -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
if [ -n "$ROUTE_URL" ]; then
    echo "Web UI URL: https://${ROUTE_URL}"
else
    echo "Creating route..."
    oc expose service pdf-slurper-web --hostname=pdf-slurper-${NAMESPACE}.apps.cloudapps.unc.edu
    echo "Web UI URL: https://pdf-slurper-${NAMESPACE}.apps.cloudapps.unc.edu"
fi

echo ""
echo "Testing web UI..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" https://${ROUTE_URL}/dashboard.html || echo "Web UI may still be starting..."

echo ""
echo "Pod status:"
oc get pods -l app=pdf-slurper
