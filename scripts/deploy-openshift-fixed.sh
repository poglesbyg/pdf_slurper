#!/bin/bash

# PDF Slurper OpenShift Deployment Script - Fixed Version 2
# This script fixes build issues with Dockerfiles

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

echo -e "${GREEN}=== PDF Slurper OpenShift Deployment Script (Fixed v2) ===${NC}"
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

# Create ImageStreams if they don't exist
echo -e "\n${GREEN}Creating/Updating ImageStreams...${NC}"
oc apply -f - <<EOF
apiVersion: v1
kind: List
items:
  - apiVersion: image.openshift.io/v1
    kind: ImageStream
    metadata:
      name: pdf-slurper
      labels:
        app: pdf-slurper
    spec:
      lookupPolicy:
        local: true
  - apiVersion: image.openshift.io/v1
    kind: ImageStream
    metadata:
      name: pdf-slurper-api
      labels:
        app: pdf-slurper
    spec:
      lookupPolicy:
        local: true
  - apiVersion: image.openshift.io/v1
    kind: ImageStream
    metadata:
      name: pdf-slurper-web
      labels:
        app: pdf-slurper
    spec:
      lookupPolicy:
        local: true
EOF

# Delete and recreate BuildConfigs with correct configuration
echo -e "\n${GREEN}Recreating BuildConfigs with correct Dockerfile references...${NC}"

# Delete existing BuildConfigs if they exist
oc delete bc pdf-slurper-api --ignore-not-found=true
oc delete bc pdf-slurper-web --ignore-not-found=true

# Create API BuildConfig
echo "Creating API BuildConfig..."
oc apply -f - <<EOF
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: pdf-slurper-api
  labels:
    app: pdf-slurper
    component: api
spec:
  output:
    to:
      kind: ImageStreamTag
      name: pdf-slurper-api:latest
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile.v2
  successfulBuildsHistoryLimit: 3
  failedBuildsHistoryLimit: 3
EOF

# Create Web BuildConfig
echo "Creating Web BuildConfig..."
oc apply -f - <<EOF
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: pdf-slurper-web
  labels:
    app: pdf-slurper
    component: web
spec:
  output:
    to:
      kind: ImageStreamTag
      name: pdf-slurper-web:latest
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile.web
  successfulBuildsHistoryLimit: 3
  failedBuildsHistoryLimit: 3
EOF

# Build API image
echo -e "\n${GREEN}Building API image...${NC}"
echo "Starting binary build with Dockerfile.v2..."

# Create a temporary directory for the build context
TEMP_BUILD_DIR=$(mktemp -d)
echo "Creating build context in $TEMP_BUILD_DIR"

# Copy necessary files to temp directory
cp -r . "$TEMP_BUILD_DIR/"
cd "$TEMP_BUILD_DIR"

# Start the build
oc start-build pdf-slurper-api --from-dir=. --follow || {
    echo -e "${RED}API build failed. Checking logs...${NC}"
    oc logs -f bc/pdf-slurper-api
    cd -
    rm -rf "$TEMP_BUILD_DIR"
    exit 1
}

cd -
rm -rf "$TEMP_BUILD_DIR"

# Build Web UI image
echo -e "\n${GREEN}Building Web UI image...${NC}"
echo "Starting binary build with Dockerfile.web..."

# Create a temporary directory for the build context
TEMP_BUILD_DIR=$(mktemp -d)
echo "Creating build context in $TEMP_BUILD_DIR"

# Copy necessary files to temp directory
cp -r . "$TEMP_BUILD_DIR/"
cd "$TEMP_BUILD_DIR"

# Start the build
oc start-build pdf-slurper-web --from-dir=. --follow || {
    echo -e "${RED}Web UI build failed. Checking logs...${NC}"
    oc logs -f bc/pdf-slurper-web
    cd -
    rm -rf "$TEMP_BUILD_DIR"
    exit 1
}

cd -
rm -rf "$TEMP_BUILD_DIR"

# Tag images for deployment
echo -e "\n${GREEN}Tagging images...${NC}"
oc tag pdf-slurper-api:latest pdf-slurper:v2
oc tag pdf-slurper-web:latest pdf-slurper-web:v2

# Apply the combined deployment configuration
echo -e "\n${GREEN}Applying deployment configuration...${NC}"

# First, let's create a modified version of the deployment yaml
cat > /tmp/deployment-combined-fixed.yaml <<'EOF'
apiVersion: v1
kind: List
metadata:
  name: pdf-slurper-combined
items:
  # ConfigMap for application configuration
  - apiVersion: v1
    kind: ConfigMap
    metadata:
      name: pdf-slurper-config
      labels:
        app: pdf-slurper
        version: v2
    data:
      PDF_SLURPER_ENV: "production"
      PDF_SLURPER_USE_NEW: "true"
      PDF_SLURPER_HOST: "0.0.0.0"
      PDF_SLURPER_PORT: "8080"
      LOG_LEVEL: "INFO"
      API_DOCS_ENABLED: "true"
      QC_AUTO_APPLY: "false"
      WORKERS: "2"

  # Secret for sensitive data
  - apiVersion: v1
    kind: Secret
    metadata:
      name: pdf-slurper-secret
      labels:
        app: pdf-slurper
        version: v2
    type: Opaque
    stringData:
      DATABASE_URL: "sqlite:////tmp/data/pdf_slurper.db"
      API_KEY: "changeme-secure-api-key"
      JWT_SECRET: "changeme-secure-jwt-secret"

  # PersistentVolumeClaim for data
  - apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: pdf-slurper-data
      labels:
        app: pdf-slurper
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi

  # Deployment for API
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
              image: image-registry.openshift-image-registry.svc:5000/NAMESPACE/pdf-slurper:v2
              imagePullPolicy: Always
              ports:
                - containerPort: 8080
                  protocol: TCP
              envFrom:
                - configMapRef:
                    name: pdf-slurper-config
                - secretRef:
                    name: pdf-slurper-secret
              volumeMounts:
                - name: data
                  mountPath: /tmp/data
                - name: uploads
                  mountPath: /app/uploads
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
          volumes:
            - name: data
              persistentVolumeClaim:
                claimName: pdf-slurper-data
            - name: uploads
              emptyDir: {}

  # Deployment for Web UI
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
              image: image-registry.openshift-image-registry.svc:5000/NAMESPACE/pdf-slurper-web:v2
              imagePullPolicy: Always
              ports:
                - containerPort: 8080
                  protocol: TCP
              resources:
                requests:
                  memory: "64Mi"
                  cpu: "60m"
                limits:
                  memory: "128Mi"
                  cpu: "100m"
              livenessProbe:
                httpGet:
                  path: /
                  port: 8080
                initialDelaySeconds: 10
                periodSeconds: 30
              readinessProbe:
                httpGet:
                  path: /
                  port: 8080
                initialDelaySeconds: 5
                periodSeconds: 10

  # Service for API
  - apiVersion: v1
    kind: Service
    metadata:
      name: pdf-slurper-api
      labels:
        app: pdf-slurper
        component: api
    spec:
      type: ClusterIP
      ports:
        - port: 8080
          targetPort: 8080
          protocol: TCP
      selector:
        app: pdf-slurper
        component: api

  # Service for Web UI
  - apiVersion: v1
    kind: Service
    metadata:
      name: pdf-slurper-web
      labels:
        app: pdf-slurper
        component: web
    spec:
      type: ClusterIP
      ports:
        - port: 8080
          targetPort: 8080
          protocol: TCP
      selector:
        app: pdf-slurper
        component: web

  # Route for main application
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
      port:
        targetPort: 8080
      tls:
        termination: edge
        insecureEdgeTerminationPolicy: Redirect

  # Route for API
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
      port:
        targetPort: 8080
      tls:
        termination: edge
        insecureEdgeTerminationPolicy: Redirect
EOF

# Replace namespace in the deployment file
sed -i.bak "s/NAMESPACE/$NAMESPACE/g" /tmp/deployment-combined-fixed.yaml

# Apply the deployment
oc apply -f /tmp/deployment-combined-fixed.yaml

# Wait for deployments to roll out
echo -e "\n${YELLOW}Waiting for deployments to complete...${NC}"
oc rollout status deployment/pdf-slurper-api --timeout=5m || {
    echo -e "${YELLOW}API deployment timeout. Checking pod status...${NC}"
    oc get pods -l app=pdf-slurper,component=api
}

oc rollout status deployment/pdf-slurper-web --timeout=5m || {
    echo -e "${YELLOW}Web deployment timeout. Checking pod status...${NC}"
    oc get pods -l app=pdf-slurper,component=web
}

# Get route URLs
echo -e "\n${GREEN}Getting route URLs...${NC}"
WEB_ROUTE=$(oc get route pdf-slurper -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
API_ROUTE=$(oc get route pdf-slurper-api -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

# Health checks
echo -e "\n${GREEN}Running health checks...${NC}"

# Check API pod
API_POD=$(oc get pod -l app=pdf-slurper,component=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ ! -z "$API_POD" ]; then
    echo "Checking API health endpoint..."
    oc exec $API_POD -- curl -s http://localhost:8080/health || echo "API health check failed"
else
    echo -e "${YELLOW}No API pod found${NC}"
fi

# Check Web pod
WEB_POD=$(oc get pod -l app=pdf-slurper,component=web -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ ! -z "$WEB_POD" ]; then
    echo "Checking Web UI..."
    oc exec $WEB_POD -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ || echo "Web UI check failed"
else
    echo -e "${YELLOW}No Web pod found${NC}"
fi

# Summary
echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "Web UI URL: ${GREEN}https://$WEB_ROUTE${NC}"
echo -e "API URL: ${GREEN}https://$API_ROUTE/api${NC}"

echo -e "\n${YELLOW}Current Status:${NC}"
echo "Deployments:"
oc get deployments -l app=pdf-slurper

echo -e "\nPods:"
oc get pods -l app=pdf-slurper

echo -e "\nRoutes:"
oc get routes -l app=pdf-slurper

echo -e "\nImageStreams:"
oc get is -l app=pdf-slurper

echo -e "\n${GREEN}Test Commands:${NC}"
echo "# Test Web UI:"
echo "curl -I https://$WEB_ROUTE/"
echo ""
echo "# Test API:"
echo "curl https://$API_ROUTE/api/health"
echo ""
echo "# View logs:"
echo "oc logs -f deployment/pdf-slurper-api"
echo "oc logs -f deployment/pdf-slurper-web"

echo -e "\n${YELLOW}If builds failed, try:${NC}"
echo "# Check build logs:"
echo "oc logs -f bc/pdf-slurper-api"
echo "oc logs -f bc/pdf-slurper-web"
echo ""
echo "# Retry builds manually:"
echo "oc start-build pdf-slurper-api --from-dir=. --follow"
echo "oc start-build pdf-slurper-web --from-dir=. --follow"

# Cleanup temp file
rm -f /tmp/deployment-combined-fixed.yaml /tmp/deployment-combined-fixed.yaml.bak
