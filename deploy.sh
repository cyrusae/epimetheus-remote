#!/bin/bash
#
# Quick deploy script for Epimetheus Remote
# Usage: ./deploy.sh [build|deploy|restart|logs|status]
#

set -e

REGISTRY="registry.dawnfire.casa"
IMAGE_NAME="epimetheus-remote"
TAG="latest"
NAMESPACE="dashboards"

function build() {
    echo "🏗️  Building Docker image..."
    docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} .
    echo "✅ Build complete"
}

function push() {
    echo "📤 Pushing to registry..."
    docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
    echo "✅ Push complete"
}

function deploy() {
    echo "🚀 Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply manifests
    kubectl apply -f k8s-deployment.yaml
    
    echo "✅ Deployment complete"
    echo ""
    echo "📊 Checking status..."
    kubectl get pods -n ${NAMESPACE}
}

function restart() {
    echo "🔄 Restarting deployment..."
    kubectl rollout restart deployment/${IMAGE_NAME} -n ${NAMESPACE}
    kubectl rollout status deployment/${IMAGE_NAME} -n ${NAMESPACE}
    echo "✅ Restart complete"
}

function logs() {
    echo "📜 Fetching logs..."
    kubectl logs -n ${NAMESPACE} -l app=${IMAGE_NAME} --tail=50 -f
}

function status() {
    echo "📊 Status:"
    echo ""
    echo "Pods:"
    kubectl get pods -n ${NAMESPACE} -l app=${IMAGE_NAME}
    echo ""
    echo "Service:"
    kubectl get svc -n ${NAMESPACE} ${IMAGE_NAME}
    echo ""
    echo "Ingress:"
    kubectl get ingress -n ${NAMESPACE} ${IMAGE_NAME}
    echo ""
    echo "Certificate:"
    kubectl get certificate -n ${NAMESPACE} ${IMAGE_NAME}-tls
}

function full_deploy() {
    build
    push
    deploy
    echo ""
    echo "🎉 Full deployment complete!"
    echo ""
    echo "Access at: https://remote.dawnfire.casa"
    echo ""
    echo "To view logs: ./deploy.sh logs"
    echo "To check status: ./deploy.sh status"
}

# Main command dispatcher
case "${1:-help}" in
    build)
        build
        ;;
    push)
        push
        ;;
    deploy)
        deploy
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    full|all)
        full_deploy
        ;;
    help|*)
        echo "Epimetheus Remote - Deploy Script"
        echo ""
        echo "Usage: ./deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  build      - Build Docker image"
        echo "  push       - Push image to registry"
        echo "  deploy     - Deploy to Kubernetes"
        echo "  restart    - Restart the deployment"
        echo "  logs       - View live logs"
        echo "  status     - Check deployment status"
        echo "  full       - Build, push, and deploy (default)"
        echo "  help       - Show this help"
        echo ""
        exit 0
        ;;
esac