#!/bin/bash

# OpenShift Deployment Script for PDF Slurper v2
# Usage: ./deploy-openshift.sh [namespace]

set -e

# Configuration
NAMESPACE="${1:-dept-barc}"
APP_NAME="pdf-slurper"
VERSION="v2"

echo "============================================"
echo "Deploying PDF Slurper v2 to OpenShift"
echo "Namespace: $NAMESPACE"
echo "============================================"

# Login check
if ! oc whoami &> /dev/null; then
    echo "❌ Not logged in to OpenShift. Please run: oc login <server>"
    exit 1
fi

echo "✓ Logged in as: $(oc whoami)"

# Create/switch to namespace
if oc get namespace "$NAMESPACE" &> /dev/null; then
    echo "✓ Namespace $NAMESPACE exists"
else
    echo "Creating namespace $NAMESPACE..."
    oc new-project "$NAMESPACE" || oc project "$NAMESPACE"
fi

oc project "$NAMESPACE"
echo "✓ Using namespace: $NAMESPACE"

# Check if image exists or needs to be built
echo ""
echo "Checking image availability..."
if oc get is pdf-slurper &> /dev/null; then
    echo "✓ ImageStream exists"
else
    echo "⚠ ImageStream not found. Building image..."
    
    # Option 1: Build from Dockerfile (if you have source code access)
    if [ -f "../Dockerfile.v2" ]; then
        echo "Building from Dockerfile.v2..."
        oc new-build --name=${APP_NAME}-${VERSION} \
            --binary \
            --strategy=docker
        
        oc start-build ${APP_NAME}-${VERSION} \
            --from-dir=.. \
            --follow
        
        # Tag the image
        oc tag ${APP_NAME}-${VERSION}:latest ${APP_NAME}:${VERSION}
    else
        echo "⚠ Dockerfile.v2 not found. You'll need to push image manually."
        echo "  Run: docker push ${REGISTRY}/${NAMESPACE}/${APP_NAME}:${VERSION}"
    fi
fi

# Generate secure secrets if not exist
if ! oc get secret pdf-slurper-secret &> /dev/null; then
    echo ""
    echo "Generating secure secrets..."
    API_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 64)
    
    oc create secret generic pdf-slurper-secret \
        --from-literal=DATABASE_URL="sqlite:////data/pdf_slurper.db" \
        --from-literal=API_KEY="$API_KEY" \
        --from-literal=JWT_SECRET="$JWT_SECRET"
    
    echo "✓ Created secret with generated keys"
    echo "  API_KEY: $API_KEY"
    echo "  (Save these values securely!)"
else
    echo "✓ Secret already exists"
fi

# Apply the deployment configuration
echo ""
echo "Applying deployment configuration..."

# Use the corrected deployment file
if [ "$2" == "direct" ]; then
    CONFIG_FILE="../openshift/deployment-direct.yaml"
else
    CONFIG_FILE="../openshift/deployment-v2.yaml"
fi

if [ -f "$CONFIG_FILE" ]; then
    # Replace the secret if using generated values
    if [ -n "$API_KEY" ]; then
        oc delete secret pdf-slurper-secret --ignore-not-found=true
        oc create secret generic pdf-slurper-secret \
            --from-literal=DATABASE_URL="sqlite:////data/pdf_slurper.db" \
            --from-literal=API_KEY="$API_KEY" \
            --from-literal=JWT_SECRET="$JWT_SECRET"
    fi
    
    # Apply the configuration (excluding the secret that we already created)
    oc apply -f "$CONFIG_FILE" | grep -v "secret/"
    
    echo "✓ Deployment configuration applied"
else
    echo "❌ Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Wait for deployment
echo ""
echo "Waiting for deployment to complete..."
oc rollout status deployment/${APP_NAME}-${VERSION} --timeout=300s

# Get route URL
ROUTE_URL=$(oc get route ${APP_NAME}-${VERSION} -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
if [ -n "$ROUTE_URL" ]; then
    echo ""
    echo "============================================"
    echo "✅ Deployment successful!"
    echo "Application URL: https://${ROUTE_URL}"
    echo "============================================"
    
    # Test the health endpoint
    echo ""
    echo "Testing health endpoint..."
    if curl -sf "https://${ROUTE_URL}/health" > /dev/null; then
        echo "✓ Health check passed"
    else
        echo "⚠ Health check failed - application may still be starting"
    fi
else
    echo "⚠ Route not found. You may need to create one manually."
fi

# Show pod status
echo ""
echo "Pod status:"
oc get pods -l app=${APP_NAME},version=${VERSION}

echo ""
echo "Deployment complete! 🚀"
echo ""
echo "Useful commands:"
echo "  View logs:    oc logs -f deploy/${APP_NAME}-${VERSION}"
echo "  Get pods:     oc get pods -l app=${APP_NAME}"
echo "  Port forward: oc port-forward deploy/${APP_NAME}-${VERSION} 8080:8080"
echo "  Scale:        oc scale deploy/${APP_NAME}-${VERSION} --replicas=3"
