#!/bin/bash

# PDF Slurper OpenShift Deployment Script - Fixed Version
# This script fixes deployment issues including:
# - IndentationError in API code (already fixed)
# - Missing Web UI deployment
# - Static file serving issues (favicon.ico)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE=${1:-dept-barc}
REGISTRY="image-registry.openshift-image-registry.svc:5000"
APP_NAME="pdf-slurper"
VERSION="v2-fixed"

echo -e "${GREEN}=== PDF Slurper OpenShift Deployment Script ===${NC}"
echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"

# Check if logged in to OpenShift
echo -e "\n${YELLOW}Checking OpenShift login...${NC}"
if ! oc whoami &> /dev/null; then
    echo -e "${RED}Error: Not logged in to OpenShift${NC}"
    echo "Please run: oc login <your-openshift-server>"
    exit 1
fi

# Switch to namespace
echo -e "\n${YELLOW}Switching to namespace: $NAMESPACE${NC}"
oc project $NAMESPACE || {
    echo -e "${RED}Error: Cannot switch to namespace $NAMESPACE${NC}"
    echo "Creating namespace..."
    oc new-project $NAMESPACE
}

# Build and push API image
echo -e "\n${GREEN}Building API image...${NC}"
echo "Using Dockerfile.v2 for API server"

# Check if BuildConfig exists
if oc get bc pdf-slurper-api &> /dev/null; then
    echo "BuildConfig exists, starting new build..."
    oc start-build pdf-slurper-api --from-dir=. --follow
else
    echo "Creating new BuildConfig..."
    oc new-build --name=pdf-slurper-api \
        --binary \
        --strategy=docker \
        --dockerfile=Dockerfile.v2
    oc start-build pdf-slurper-api --from-dir=. --follow
fi

# Build and push Web UI image
echo -e "\n${GREEN}Building Web UI image...${NC}"
echo "Using Dockerfile.web for static file serving"

# Check if BuildConfig exists
if oc get bc pdf-slurper-web &> /dev/null; then
    echo "BuildConfig exists, starting new build..."
    oc start-build pdf-slurper-web --from-dir=. --follow
else
    echo "Creating new BuildConfig..."
    oc new-build --name=pdf-slurper-web \
        --binary \
        --strategy=docker \
        --dockerfile=Dockerfile.web
    oc start-build pdf-slurper-web --from-dir=. --follow
fi

# Tag images
echo -e "\n${GREEN}Tagging images...${NC}"
oc tag pdf-slurper-api:latest pdf-slurper:v2
oc tag pdf-slurper-web:latest pdf-slurper-web:latest

# Apply combined deployment
echo -e "\n${GREEN}Applying combined deployment configuration...${NC}"
echo "This includes both API and Web UI components"

# Update the image references in the deployment
sed "s|dept-barc|$NAMESPACE|g" openshift/deployment-combined.yaml | \
sed "s|image-registry.openshift-image-registry.svc:5000/dept-barc/pdf-slurper:v2|$REGISTRY/$NAMESPACE/pdf-slurper:v2|g" | \
sed "s|image-registry.openshift-image-registry.svc:5000/dept-barc/pdf-slurper-web:latest|$REGISTRY/$NAMESPACE/pdf-slurper-web:latest|g" | \
oc apply -f -

# Wait for deployments
echo -e "\n${YELLOW}Waiting for deployments to roll out...${NC}"
oc rollout status deployment/pdf-slurper-v2 --timeout=5m
oc rollout status deployment/pdf-slurper-web --timeout=5m

# Get route URL
ROUTE_URL=$(oc get route pdf-slurper -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
if [ -z "$ROUTE_URL" ]; then
    echo -e "${YELLOW}No route found, creating one...${NC}"
    oc expose svc/pdf-slurper-web --hostname=pdf-slurper-$NAMESPACE.apps.cloudapps.unc.edu
    ROUTE_URL=$(oc get route pdf-slurper-web -o jsonpath='{.spec.host}')
fi

# Health check
echo -e "\n${GREEN}Running health checks...${NC}"
echo "Checking API health endpoint..."
API_POD=$(oc get pod -l app=pdf-slurper,component=api -o jsonpath='{.items[0].metadata.name}')
oc exec $API_POD -- curl -s http://localhost:8080/health || echo "API health check warning"

echo "Checking Web UI..."
WEB_POD=$(oc get pod -l app=pdf-slurper,component=web -o jsonpath='{.items[0].metadata.name}')
oc exec $WEB_POD -- curl -s http://localhost:8080/dashboard.html | head -n 5 || echo "Web UI check warning"

# Summary
echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "Web UI URL: ${GREEN}https://$ROUTE_URL${NC}"
echo -e "API Health: ${GREEN}https://$ROUTE_URL/api/health${NC}"
echo -e "API Docs: ${GREEN}https://$ROUTE_URL/api/docs${NC}"

echo -e "\n${YELLOW}Deployment Status:${NC}"
oc get deployments -l app=pdf-slurper
echo ""
oc get pods -l app=pdf-slurper
echo ""
oc get routes -l app=pdf-slurper

echo -e "\n${GREEN}Quick Test Commands:${NC}"
echo "# Test Web UI:"
echo "curl -I https://$ROUTE_URL/"
echo ""
echo "# Test API:"
echo "curl https://$ROUTE_URL/api/health"
echo ""
echo "# View logs:"
echo "oc logs -f deployment/pdf-slurper-v2"
echo "oc logs -f deployment/pdf-slurper-web"

echo -e "\n${YELLOW}Troubleshooting:${NC}"
echo "If you encounter issues, check:"
echo "1. Pod status: oc get pods -l app=pdf-slurper"
echo "2. Pod logs: oc logs <pod-name>"
echo "3. Events: oc get events --sort-by='.lastTimestamp'"
echo "4. Describe pod: oc describe pod <pod-name>"
