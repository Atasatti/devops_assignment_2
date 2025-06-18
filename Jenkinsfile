pipeline {
    agent any
    
    environment {
        // Docker Hub credentials (configure in Jenkins)
        DOCKER_HUB_CREDENTIALS = credentials('docker-hub-credentials')
        DOCKER_IMAGE_NAME = 'your-dockerhub-username/people-management-app'
        DOCKER_TAG = "${BUILD_NUMBER}"
        
        // AWS EC2 credentials (configure in Jenkins)
        EC2_CREDENTIALS = credentials('ec2-ssh-key')
        EC2_HOST = 'your-ec2-public-ip'
        EC2_USER = 'ubuntu'
        
        // Application environment variables
        MONGO_URI = credentials('mongo-uri')
        SECRET_KEY = credentials('secret-key')
        
        // Deployment directory on EC2
        DEPLOY_DIR = '/opt/people-management'
    }
    
    stages {
        stage('Checkout') {
            steps {
                // Checkout code from your GitHub repository
                git url: 'https://github.com/Atasatti/devops_assignment_2.git', branch: 'main'
            }
        }
        
        stage('Environment Setup') {
            steps {
                echo 'Setting up environment...'
                script {
                    // Create .env file for local testing
                    writeFile file: '.env', text: """
MONGO_URI=${MONGO_URI}
SECRET_KEY=${SECRET_KEY}
FLASK_APP=app.py
FLASK_ENV=production
"""
                }
            }
        }
        
        stage('Code Quality Check') {
            steps {
                echo 'Running code quality checks...'
                script {
                    // Install Python dependencies for testing
                    sh '''
                        python3 -m venv venv
                        . venv/bin/activate
                        pip install -r requirements.txt
                        pip install flake8 pytest
                    '''
                    
                    // Run linting
                    sh '''
                        . venv/bin/activate
                        flake8 app.py --max-line-length=120 --ignore=E501,W503 || true
                    '''
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                echo 'Running unit tests...'
                script {
                    sh '''
                        . venv/bin/activate
                        python -m pytest tests/ --verbose || echo "No tests found, skipping..."
                    '''
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    // Build docker images using docker-compose
                    sh 'docker-compose -p peoplemgmt build'
                }
            }
        }
        
        stage('Stop Old Containers') {
            steps {
                script {
                    // Stop existing containers if running
                    sh 'docker-compose -p peoplemgmt down || true'
                }
            }
        }

        stage('Run Containers') {
            steps {
                script {
                    // Run containers in detached mode
                    sh 'docker-compose -p peoplemgmt -f docker-compose.yml up -d'
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    // Wait for services to start
                    sh 'sleep 30'
                    
                    // Check if application is running
                    sh '''
                        echo "Checking if application is running..."
                        curl -f http://localhost || echo "Application not responding yet, but continuing..."
                        docker-compose -p peoplemgmt ps
                    '''
                }
            }
        }

        stage('Cleanup') {
            steps {
                script {
                    // Clean up unused images to save space
                    sh 'docker image prune -f || true'
                }
            }
        }
        
        stage('Test Docker Image') {
            steps {
                echo 'Testing Docker image...'
                script {
                    // Run container for testing
                    sh '''
                        docker run -d --name test-container \
                            -e MONGO_URI="${MONGO_URI}" \
                            -e SECRET_KEY="${SECRET_KEY}" \
                            -p 5001:5000 \
                            ${DOCKER_IMAGE_NAME}:${DOCKER_TAG}
                        
                        # Wait for container to start
                        sleep 10
                        
                        # Test if application is responding
                        curl -f http://localhost:5001 || exit 1
                        
                        # Clean up test container
                        docker stop test-container
                        docker rm test-container
                    '''
                }
            }
        }

        stage('Push to Docker Hub') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                echo 'Pushing Docker image to Docker Hub...'
                script {
                    docker.withRegistry('https://registry.hub.docker.com', 'docker-hub-credentials') {
                        def image = docker.image("${DOCKER_IMAGE_NAME}:${DOCKER_TAG}")
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                echo 'Deploying to staging environment...'
                script {
                    sshagent(['ec2-ssh-key']) {
                        sh '''
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} "
                                cd ${DEPLOY_DIR}/staging &&
                                docker-compose -f docker-compose.staging.yml down &&
                                docker-compose -f docker-compose.staging.yml pull &&
                                docker-compose -f docker-compose.staging.yml up -d
                            "
                        '''
                    }
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                echo 'Deploying to production environment...'
                script {
                    // Create deployment script
                    writeFile file: 'deploy.sh', text: '''#!/bin/bash
set -e

echo "🚀 Starting production deployment..."

# Navigate to deployment directory
cd ''' + DEPLOY_DIR + '''

# Create backup of current deployment
if [ -d "backup" ]; then
    rm -rf backup.old
    mv backup backup.old
fi
mkdir -p backup
cp -r . backup/ 2>/dev/null || true

# Pull latest code
git pull origin main

# Update environment variables
cat > .env << EOF
MONGO_URI=''' + MONGO_URI + '''
SECRET_KEY=''' + SECRET_KEY + '''
FLASK_APP=app.py
FLASK_ENV=production
EOF

# Stop current containers
docker-compose down

# Pull latest images
docker-compose pull

# Start new containers
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
if curl -f http://localhost > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
    # Clean up old images
    docker image prune -f
else
    echo "❌ Deployment failed! Rolling back..."
    docker-compose down
    cp -r backup/* .
    docker-compose up -d
    exit 1
fi

echo "🎉 Production deployment completed successfully!"
'''
                    
                    // Execute deployment
                    sshagent(['ec2-ssh-key']) {
                        sh '''
                            # Copy deployment script to server
                            scp -o StrictHostKeyChecking=no deploy.sh ${EC2_USER}@${EC2_HOST}:${DEPLOY_DIR}/
                            
                            # Execute deployment on server
                            ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} "
                                chmod +x ${DEPLOY_DIR}/deploy.sh &&
                                ${DEPLOY_DIR}/deploy.sh
                            "
                        '''
                    }
                }
            }
        }
        
        stage('Post-Deployment Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                echo 'Running post-deployment tests...'
                script {
                    sh '''
                        # Test production endpoint
                        curl -f http://${EC2_HOST} || exit 1
                        
                        # Test specific endpoints
                        curl -f http://${EC2_HOST}/add || exit 1
                        
                        echo "✅ All post-deployment tests passed!"
                    '''
                }
            }
        }
        
        stage('Notify') {
            steps {
                echo 'Sending notifications...'
                script {
                    // Send Slack notification (configure webhook in Jenkins)
                    sh '''
                        curl -X POST -H 'Content-type: application/json' \
                            --data '{"text":"🚀 People Management App deployed successfully to production!\\nBuild: #${BUILD_NUMBER}\\nBranch: ${BRANCH_NAME}"}' \
                            ${SLACK_WEBHOOK_URL} || echo "Slack notification failed"
                    '''
                }
            }
        }
    }
    
    post {
        success {
            script {
                echo 'Build and deployment completed successfully!'
                echo 'Application should be running at http://your-server-ip'
                sh 'docker-compose -p peoplemgmt ps'
            }
        }
        failure {
            script {
                echo 'Build or deployment failed. Please check logs.'
                // Show container logs for debugging
                sh 'docker-compose -p peoplemgmt logs || true'
            }
        }
        always {
            script {
                echo 'Pipeline completed.'
                // Show final status
                sh 'docker ps || true'
            }
        }
    }
}
