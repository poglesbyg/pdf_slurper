#!/bin/bash

# OpenShift Deployment Script for PDF Slurper v2 with CRUD
# Usage: ./deploy-crud-openshift.sh [namespace] [openshift-server]

set -e

# Configuration
NAMESPACE="${1:-dept-barc}"
OPENSHIFT_SERVER="${2:-https://api.openshift.example.com:6443}"
APP_NAME="pdf-slurper"
VERSION="v2-crud"
IMAGE_TAG="2.1.0-crud"

echo "============================================"
echo "Deploying PDF Slurper v2 with CRUD to OpenShift"
echo "Namespace: $NAMESPACE"
echo "Server: $OPENSHIFT_SERVER"
echo "============================================"

# Check if logged in to OpenShift (simulation mode if not available)
if command -v oc &> /dev/null; then
    echo "✓ OpenShift CLI found"
    
    # Login check
    if ! oc whoami &> /dev/null; then
        echo "⚠️  Not logged in to OpenShift"
        echo "Please run: oc login $OPENSHIFT_SERVER"
        echo ""
        echo "Continuing in simulation mode..."
        SIMULATION_MODE=true
    else
        echo "✓ Logged in as: $(oc whoami)"
        SIMULATION_MODE=false
    fi
else
    echo "⚠️  OpenShift CLI not found. Running in simulation mode..."
    SIMULATION_MODE=true
fi

# Load secrets from file
if [ -f "deployment_secrets.txt" ]; then
    echo "✓ Loading secrets from deployment_secrets.txt"
    source <(grep = deployment_secrets.txt | sed 's/ //g')
else
    echo "⚠️  deployment_secrets.txt not found. Using default values..."
    API_KEY="demo-api-key"
    JWT_SECRET="demo-jwt-secret"
    SECRET_KEY="demo-secret-key"
fi

if [ "$SIMULATION_MODE" = true ]; then
    echo ""
    echo "=== SIMULATION MODE ==="
    echo "The following commands would be executed:"
    echo ""
    
    echo "1. Create/switch namespace:"
    echo "   oc project $NAMESPACE"
    echo ""
    
    echo "2. Tag and push Docker image:"
    echo "   docker tag pdf-slurper:v2-crud default-route-openshift-image-registry.apps.cloudapps.unc.edu/$NAMESPACE/pdf-slurper:$IMAGE_TAG"
    echo "   docker push default-route-openshift-image-registry.apps.cloudapps.unc.edu/$NAMESPACE/pdf-slurper:$IMAGE_TAG"
    echo ""
    
    echo "3. Create secret:"
    echo "   oc create secret generic pdf-slurper-secret \\"
    echo "     --from-literal=API_KEY='$API_KEY' \\"
    echo "     --from-literal=JWT_SECRET='$JWT_SECRET' \\"
    echo "     --from-literal=SECRET_KEY='$SECRET_KEY' \\"
    echo "     --from-literal=DATABASE_URL='sqlite:////data/pdf_slurper.db'"
    echo ""
    
    echo "4. Apply deployment configuration:"
    echo "   sed 's/NAMESPACE/$NAMESPACE/g' openshift/deployment-crud.yaml | oc apply -f -"
    echo ""
    
    echo "5. Wait for rollout:"
    echo "   oc rollout status deployment/pdf-slurper-v2"
    echo ""
    
    echo "6. Get route URL:"
    echo "   oc get route pdf-slurper-v2 -o jsonpath='{.spec.host}'"
    echo ""
else
    # Actual deployment commands
    
    # Create/switch to namespace
    if oc get namespace "$NAMESPACE" &> /dev/null; then
        echo "✓ Namespace $NAMESPACE exists"
    else
        echo "Creating namespace $NAMESPACE..."
        oc new-project "$NAMESPACE"
    fi
    oc project "$NAMESPACE"
    
    # Get registry route
    REGISTRY=$(oc get route -n openshift-image-registry default-route -o jsonpath='{.spec.host}' 2>/dev/null || echo "image-registry.openshift-image-registry.svc:5000")
    echo "✓ Using registry: $REGISTRY"
    
    # Tag and push image
    echo "Tagging Docker image..."
    docker tag pdf-slurper:v2-crud $REGISTRY/$NAMESPACE/pdf-slurper:$IMAGE_TAG
    
    echo "Pushing to OpenShift registry..."
    docker login -u $(oc whoami) -p $(oc whoami -t) $REGISTRY
    docker push $REGISTRY/$NAMESPACE/pdf-slurper:$IMAGE_TAG
    
    # Create or update secret
    echo "Creating/updating secret..."
    oc delete secret pdf-slurper-secret --ignore-not-found=true
    oc create secret generic pdf-slurper-secret \
        --from-literal=API_KEY="$API_KEY" \
        --from-literal=JWT_SECRET="$JWT_SECRET" \
        --from-literal=SECRET_KEY="$SECRET_KEY" \
        --from-literal=DATABASE_URL="sqlite:////data/pdf_slurper.db"
    
    # Apply deployment configuration
    echo "Applying deployment configuration..."
    sed "s/NAMESPACE/$NAMESPACE/g" openshift/deployment-crud.yaml | oc apply -f -
    
    # Wait for rollout
    echo "Waiting for deployment to complete..."
    oc rollout status deployment/pdf-slurper-v2 --timeout=300s
    
    # Get route URL
    ROUTE_URL=$(oc get route pdf-slurper-v2 -o jsonpath='{.spec.host}')
    
    echo ""
    echo "============================================"
    echo "✅ Deployment successful!"
    echo "Application URL: https://$ROUTE_URL"
    echo "============================================"
    
    # Test health endpoint
    echo ""
    echo "Testing health endpoint..."
    if curl -sf "https://$ROUTE_URL/health" > /dev/null; then
        echo "✓ Health check passed"
    else
        echo "⚠️  Health check failed - application may still be starting"
    fi
fi

# Clean up Docker test container
if docker ps | grep -q pdf-slurper-test; then
    echo ""
    echo "Cleaning up local test container..."
    docker stop pdf-slurper-test
    docker rm pdf-slurper-test
fi

echo ""
echo "=== Post-Deployment Steps ==="
echo ""
echo "1. Test CRUD operations:"
echo "   # List submissions"
echo "   curl https://$ROUTE_URL/api/v1/submissions/"
echo ""
echo "   # Create sample"
echo "   curl -X POST https://$ROUTE_URL/api/v1/submissions/{id}/samples \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"name\": \"Test Sample\"}'"
echo ""
echo "2. Monitor logs:"
echo "   oc logs -f deployment/pdf-slurper-v2"
echo ""
echo "3. Scale if needed:"
echo "   oc scale deployment/pdf-slurper-v2 --replicas=3"
echo ""
echo "4. Check resource usage:"
echo "   oc adm top pod -l app=pdf-slurper"
echo ""
echo "Deployment complete! 🚀"
