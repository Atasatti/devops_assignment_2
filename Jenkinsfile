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
                    
                    // Check if containers are running
                    sh 'docker-compose -p peoplemgmt ps'
                    
                    // Try to check if application is responding
                    sh 'curl -f http://localhost || echo "Application might still be starting..."'
                }
            }
        }
    }
    
    post {
        success {
            echo 'Build and deployment completed successfully!'
            echo 'Your application should be running now.'
        }
        failure {
            echo 'Build or deployment failed. Please check the logs above.'
        }
        always {
            echo 'Pipeline execution completed.'
        }
    }
}
