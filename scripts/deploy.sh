#!/bin/bash
# Deployment script for PDF Slurper v2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT=${1:-pdf-slurper}
ENVIRONMENT=${2:-staging}  # staging or production
VERSION=${3:-v2}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PDF Slurper v2 Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Project: ${PROJECT}"
echo -e "Environment: ${ENVIRONMENT}"
echo -e "Version: ${VERSION}"
echo ""

# Function to check if logged in to OpenShift
check_oc_login() {
    if ! oc whoami &> /dev/null; then
        echo -e "${RED}Error: Not logged in to OpenShift${NC}"
        echo "Please run: oc login <cluster-url>"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Logged in as: $(oc whoami)"
}

# Function to switch project
switch_project() {
    if ! oc project ${PROJECT} &> /dev/null; then
        echo -e "${YELLOW}Creating project: ${PROJECT}${NC}"
        oc new-project ${PROJECT}
    else
        echo -e "${GREEN}✓${NC} Using project: ${PROJECT}"
    fi
}

# Function to deploy application
deploy_app() {
    echo -e "\n${BLUE}Deploying application...${NC}"
    
    # Apply configuration based on environment
    if [ "$ENVIRONMENT" == "production" ]; then
        echo -e "${YELLOW}Applying production configuration...${NC}"
        oc apply -f openshift/deployment-v2.yaml
        
        # Scale for production
        oc scale deployment/pdf-slurper-v2 --replicas=3
        
        # Set production environment variables
        oc set env deployment/pdf-slurper-v2 \
            PDF_SLURPER_ENV=production \
            API_DOCS_ENABLED=false \
            LOG_LEVEL=WARNING
    else
        echo -e "${YELLOW}Applying staging configuration...${NC}"
        oc apply -f openshift/deployment-v2.yaml
        
        # Keep minimal replicas for staging
        oc scale deployment/pdf-slurper-v2 --replicas=1
        
        # Set staging environment variables
        oc set env deployment/pdf-slurper-v2 \
            PDF_SLURPER_ENV=staging \
            API_DOCS_ENABLED=true \
            LOG_LEVEL=DEBUG
    fi
    
    echo -e "${GREEN}✓${NC} Application deployed"
}

# Function to trigger build
trigger_build() {
    echo -e "\n${BLUE}Building application image...${NC}"
    
    # Start build
    oc start-build pdf-slurper-v2 --wait
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Build completed successfully"
    else
        echo -e "${RED}✗${NC} Build failed"
        exit 1
    fi
}

# Function to wait for deployment
wait_for_deployment() {
    echo -e "\n${BLUE}Waiting for deployment to complete...${NC}"
    
    oc rollout status deployment/pdf-slurper-v2 --timeout=300s
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Deployment completed"
    else
        echo -e "${RED}✗${NC} Deployment failed"
        exit 1
    fi
}

# Function to run health checks
run_health_checks() {
    echo -e "\n${BLUE}Running health checks...${NC}"
    
    # Get route URL
    ROUTE_URL=$(oc get route pdf-slurper-v2 -o jsonpath='{.spec.host}')
    
    # Check health endpoint
    if curl -sf "https://${ROUTE_URL}/health" > /dev/null; then
        echo -e "${GREEN}✓${NC} Health check passed"
    else
        echo -e "${YELLOW}⚠${NC} Health check failed (may need more time)"
    fi
    
    # Check ready endpoint
    if curl -sf "https://${ROUTE_URL}/ready" > /dev/null; then
        echo -e "${GREEN}✓${NC} Readiness check passed"
    else
        echo -e "${YELLOW}⚠${NC} Readiness check failed (may need more time)"
    fi
    
    echo -e "\nApplication URL: ${GREEN}https://${ROUTE_URL}${NC}"
    if [ "$ENVIRONMENT" != "production" ]; then
        echo -e "API Documentation: ${GREEN}https://${ROUTE_URL}/api/docs${NC}"
    fi
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "\n${BLUE}Setting up monitoring...${NC}"
    
    # Create ServiceMonitor for Prometheus (if available)
    cat <<EOF | oc apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pdf-slurper-v2
  labels:
    app: pdf-slurper
    version: v2
spec:
  selector:
    matchLabels:
      app: pdf-slurper
      version: v2
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
EOF
    
    echo -e "${GREEN}✓${NC} Monitoring configured"
}

# Function to display deployment info
display_info() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Deployment Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    echo -e "\n${YELLOW}Pods:${NC}"
    oc get pods -l app=pdf-slurper,version=v2
    
    echo -e "\n${YELLOW}Services:${NC}"
    oc get svc -l app=pdf-slurper
    
    echo -e "\n${YELLOW}Routes:${NC}"
    oc get routes -l app=pdf-slurper
    
    echo -e "\n${YELLOW}Resources:${NC}"
    oc describe deployment pdf-slurper-v2 | grep -E "Limits|Requests" -A 2
}

# Function for rollback
rollback() {
    echo -e "\n${RED}Rolling back deployment...${NC}"
    oc rollout undo deployment/pdf-slurper-v2
    oc rollout status deployment/pdf-slurper-v2
    echo -e "${GREEN}✓${NC} Rollback completed"
}

# Main deployment flow
main() {
    check_oc_login
    switch_project
    
    # Ask for confirmation in production
    if [ "$ENVIRONMENT" == "production" ]; then
        echo -e "\n${YELLOW}⚠ WARNING: Deploying to PRODUCTION${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo -e "${RED}Deployment cancelled${NC}"
            exit 0
        fi
    fi
    
    deploy_app
    trigger_build
    wait_for_deployment
    
    if [ "$ENVIRONMENT" != "production" ]; then
        setup_monitoring
    fi
    
    run_health_checks
    display_info
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Handle command line arguments
case "${4:-deploy}" in
    deploy)
        main
        ;;
    rollback)
        check_oc_login
        switch_project
        rollback
        ;;
    status)
        check_oc_login
        switch_project
        display_info
        ;;
    *)
        echo "Usage: $0 <project> <environment> <version> [deploy|rollback|status]"
        exit 1
        ;;
esac
