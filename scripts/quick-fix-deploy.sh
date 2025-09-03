#!/bin/bash

# Quick fix for OpenShift deployment issues
# This script directly addresses the Dockerfile path problems

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

NAMESPACE=${1:-dept-barc}

echo -e "${GREEN}=== Quick Fix Deployment Script ===${NC}"
echo "Namespace: $NAMESPACE"

# Ensure we're in the project namespace
oc project $NAMESPACE

# Step 1: Create ImageStreams
echo -e "\n${GREEN}Step 1: Creating ImageStreams...${NC}"
oc create is pdf-slurper --dry-run=client -o yaml | oc apply -f -
oc create is pdf-slurper-api --dry-run=client -o yaml | oc apply -f -
oc create is pdf-slurper-web --dry-run=client -o yaml | oc apply -f -

# Step 2: Delete old BuildConfigs
echo -e "\n${GREEN}Step 2: Cleaning up old BuildConfigs...${NC}"
oc delete bc pdf-slurper-api --ignore-not-found=true
oc delete bc pdf-slurper-web --ignore-not-found=true

# Step 3: Create new BuildConfigs without dockerfilePath (use default Dockerfile)
echo -e "\n${GREEN}Step 3: Creating fixed BuildConfigs...${NC}"

# For API - we'll rename Dockerfile.v2 temporarily
echo "Creating API BuildConfig (using Dockerfile.v2)..."
oc new-build --name=pdf-slurper-api \
  --image-stream=pdf-slurper-api:latest \
  --binary=true \
  --strategy=docker || true

# For Web UI - we'll use Dockerfile.web  
echo "Creating Web UI BuildConfig (using Dockerfile.web)..."
oc new-build --name=pdf-slurper-web \
  --image-stream=pdf-slurper-web:latest \
  --binary=true \
  --strategy=docker || true

# Step 4: Build API with correct Dockerfile
echo -e "\n${GREEN}Step 4: Building API image...${NC}"
# Create a temporary build directory for API
TEMP_API_DIR=$(mktemp -d)
echo "Preparing API build context in $TEMP_API_DIR"

# Copy everything needed for the API build
cp -r pyproject.toml README.md pdf_slurper src "$TEMP_API_DIR/"
cp Dockerfile.v2 "$TEMP_API_DIR/Dockerfile"  # Rename to default Dockerfile

# Start the API build
cd "$TEMP_API_DIR"
oc start-build pdf-slurper-api --from-dir=. --follow || {
    echo -e "${RED}API build failed${NC}"
    cd -
    rm -rf "$TEMP_API_DIR"
    exit 1
}
cd -
rm -rf "$TEMP_API_DIR"

# Step 5: Build Web UI with correct Dockerfile
echo -e "\n${GREEN}Step 5: Building Web UI image...${NC}"
# Create a temporary build directory for Web UI
TEMP_WEB_DIR=$(mktemp -d)
echo "Preparing Web UI build context in $TEMP_WEB_DIR"

# Copy everything needed for the Web UI build
cp -r nginx web-static "$TEMP_WEB_DIR/" 2>/dev/null || true
cp Dockerfile.web "$TEMP_WEB_DIR/Dockerfile"  # Rename to default Dockerfile

# Start the Web UI build
cd "$TEMP_WEB_DIR"
oc start-build pdf-slurper-web --from-dir=. --follow || {
    echo -e "${RED}Web UI build failed${NC}"
    cd -
    rm -rf "$TEMP_WEB_DIR"
    exit 1
}
cd -
rm -rf "$TEMP_WEB_DIR"

# Step 6: Tag images
echo -e "\n${GREEN}Step 6: Tagging images...${NC}"
oc tag pdf-slurper-api:latest pdf-slurper:v2
oc tag pdf-slurper-web:latest pdf-slurper-web:v2

# Step 7: Deploy the applications
echo -e "\n${GREEN}Step 7: Deploying applications...${NC}"

# Apply minimal deployment configuration
cat <<EOF | oc apply -f -
apiVersion: v1
kind: List
items:
  # ConfigMap
  - apiVersion: v1
    kind: ConfigMap
    metadata:
      name: pdf-slurper-config
    data:
      PDF_SLURPER_ENV: "production"
      PDF_SLURPER_USE_NEW: "true"
      PDF_SLURPER_HOST: "0.0.0.0"
      PDF_SLURPER_PORT: "8080"
      LOG_LEVEL: "INFO"
      API_DOCS_ENABLED: "true"

  # Secret
  - apiVersion: v1
    kind: Secret
    metadata:
      name: pdf-slurper-secret
    stringData:
      DATABASE_URL: "sqlite:////tmp/data/pdf_slurper.db"
      API_KEY: "test-key-replace-in-production"
      JWT_SECRET: "test-secret-replace-in-production"

  # API Deployment
  - apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: pdf-slurper-api
      labels:
        app: pdf-slurper
        component: api
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: pdf-slurper
          component: api
      template:
        metadata:
          labels:
            app: pdf-slurper
            component: api
        spec:
          containers:
          - name: api
            image: image-registry.openshift-image-registry.svc:5000/$NAMESPACE/pdf-slurper:v2
            ports:
            - containerPort: 8080
            envFrom:
            - configMapRef:
                name: pdf-slurper-config
            - secretRef:
                name: pdf-slurper-secret
            resources:
              requests:
                memory: "64Mi"
                cpu: "60m"
              limits:
                memory: "256Mi"
                cpu: "200m"
            livenessProbe:
              httpGet:
                path: /health
                port: 8080
              initialDelaySeconds: 30
              periodSeconds: 30
            readinessProbe:
              httpGet:
                path: /ready
                port: 8080
              initialDelaySeconds: 10
              periodSeconds: 10
            volumeMounts:
            - name: data
              mountPath: /tmp/data
          volumes:
          - name: data
            emptyDir: {}

  # Web UI Deployment
  - apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: pdf-slurper-web
      labels:
        app: pdf-slurper
        component: web
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: pdf-slurper
          component: web
      template:
        metadata:
          labels:
            app: pdf-slurper
            component: web
        spec:
          containers:
          - name: web
            image: image-registry.openshift-image-registry.svc:5000/$NAMESPACE/pdf-slurper-web:v2
            ports:
            - containerPort: 8080
            resources:
              requests:
                memory: "64Mi"
                cpu: "60m"
              limits:
                memory: "128Mi"
                cpu: "100m"

  # API Service
  - apiVersion: v1
    kind: Service
    metadata:
      name: pdf-slurper-api
      labels:
        app: pdf-slurper
        component: api
    spec:
      ports:
      - port: 8080
        targetPort: 8080
      selector:
        app: pdf-slurper
        component: api

  # Web Service
  - apiVersion: v1
    kind: Service
    metadata:
      name: pdf-slurper-web
      labels:
        app: pdf-slurper
        component: web
    spec:
      ports:
      - port: 8080
        targetPort: 8080
      selector:
        app: pdf-slurper
        component: web

  # Main Route (Web UI)
  - apiVersion: route.openshift.io/v1
    kind: Route
    metadata:
      name: pdf-slurper
      labels:
        app: pdf-slurper
    spec:
      to:
        kind: Service
        name: pdf-slurper-web
      tls:
        termination: edge
        insecureEdgeTerminationPolicy: Redirect

  # API Route
  - apiVersion: route.openshift.io/v1
    kind: Route
    metadata:
      name: pdf-slurper-api
      labels:
        app: pdf-slurper
    spec:
      path: /api
      to:
        kind: Service
        name: pdf-slurper-api
      tls:
        termination: edge
        insecureEdgeTerminationPolicy: Redirect
EOF

# Step 8: Wait for rollout
echo -e "\n${GREEN}Step 8: Waiting for rollout...${NC}"
oc rollout status deployment/pdf-slurper-api --timeout=3m || echo "API rollout timeout"
oc rollout status deployment/pdf-slurper-web --timeout=3m || echo "Web rollout timeout"

# Step 9: Display status
echo -e "\n${GREEN}=== Deployment Status ===${NC}"
echo "Pods:"
oc get pods -l app=pdf-slurper

echo -e "\nServices:"
oc get svc -l app=pdf-slurper

echo -e "\nRoutes:"
oc get routes -l app=pdf-slurper

echo -e "\nImageStreams:"
oc get is | grep pdf-slurper

# Get URLs
WEB_URL=$(oc get route pdf-slurper -o jsonpath='{.spec.host}' 2>/dev/null || echo "not-found")
API_URL=$(oc get route pdf-slurper-api -o jsonpath='{.spec.host}' 2>/dev/null || echo "not-found")

echo -e "\n${GREEN}=== Access URLs ===${NC}"
echo "Web UI: https://$WEB_URL"
echo "API: https://$API_URL/api"
echo "API Health: https://$API_URL/api/health"

echo -e "\n${GREEN}Test with:${NC}"
echo "curl -k https://$WEB_URL/"
echo "curl -k https://$API_URL/api/health"

echo -e "\n${YELLOW}If builds still fail, try manual Docker build:${NC}"
echo "# Build locally and push:"
echo "docker build -f Dockerfile.v2 -t $NAMESPACE/pdf-slurper:v2 ."
echo "docker build -f Dockerfile.web -t $NAMESPACE/pdf-slurper-web:v2 ."
echo "# Then push to OpenShift registry"
