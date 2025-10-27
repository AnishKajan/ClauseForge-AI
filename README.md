# ClauseForge AI Contract Analyzer

An enterprise-grade AI platform that helps lawyers, compliance officers, and businesses analyze, compare, and summarize contracts using Retrieval-Augmented Generation (RAG) powered by pgvector, LangChain, and Claude.

## 🚀 Quick Start

### Prerequisites Setup (Task 0)

1. **Install Required Software**
   ```bash
   # Verify current installations
   ./scripts/verify-prerequisites.sh
   ```

2. **Initialize Environment**
   ```bash
   # Create .env file and generate secrets
   ./scripts/init-env.sh
   ```

3. **Configure API Keys**
   Edit `.env` file with your actual API keys:
   - **Anthropic Claude API**: Get from https://console.anthropic.com
   - **OpenAI API**: Get from https://platform.openai.com/api-keys  
   - **Stripe API**: Get from https://dashboard.stripe.com/apikeys

4. **Setup AWS Resources** (Optional for local development)
   ```bash
   # Configure AWS CLI first
   aws configure
   
   # Create S3 buckets, SQS queues, and IAM policies
   ./aws-setup/setup-aws-resources.sh
   ```

5. **Configure Stripe Webhooks**
   Follow the guide in `stripe-setup/webhook-config.md`

### System Requirements

| Component | Minimum Version | Status |
|-----------|----------------|---------|
| Python | 3.11+ | ✅ |
| Node.js | 20+ | ⚠️ (18.20.8 installed) |
| Docker | Latest | ✅ |
| Docker Compose | v2+ | ✅ |

### Tech Stack Architecture

![ClauseForge AI Tech Stack](frontend/public/ClauseForge-AI%20TechStack.jpg)

Our comprehensive tech stack includes:
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python
- **Database**: PostgreSQL with pgvector for semantic search
- **AI Services**: Claude API (LLM) and LangChain for RAG
- **Cloud Infrastructure**: Azure services for hosting and storage
- **Authentication**: Auth0 with Microsoft SSO integration
- **Payments**: Stripe API for billing management
- **CI/CD**: GitHub Actions for automated deployment

## 📋 Implementation Plan

This project follows a structured implementation approach with 13 main tasks:

- **Task 0**: ✅ Prerequisites and environment setup
- **Task 1**: ✅ Project structure and development environment 
- **Task 2**: ⏳ Database foundation and multi-tenancy
- **Task 3**: ⏳ Authentication and authorization system
- **Task 4**: ⏳ Core storage and file management
- **Task 5**: ⏳ Document processing and ingestion pipeline
- **Task 6**: ⏳ RAG query system and AI integration
- **Task 7**: ⏳ Compliance analysis and risk assessment
- **Task 8**: ⏳ Contract comparison functionality
- **Task 9**: ⏳ Billing and subscription management
- **Task 10**: ⏳ Enterprise features and SSO
- **Task 11**: ⏳ Security, monitoring, and production readiness
- **Task 12**: ⏳ Quality assurance and testing (optional)
- **Task 13**: ⏳ Release and deployment management

## 🛠️ Development Setup

### Local Development Environment

1. **Start Infrastructure Services**
   ```bash
   # Will be created in Task 1
   docker-compose up -d postgres redis localstack
   ```

2. **Backend Development**
   ```bash
   # Will be configured in Task 1
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

3. **Frontend Development**
   ```bash
   # Will be configured in Task 1
   cd frontend
   npm install
   npm run dev
   ```

### Key Features

- **🤖 AI-Powered Analysis**: Claude 3 Sonnet/Opus for contract analysis
- **🔍 Semantic Search**: pgvector-powered document retrieval
- **📊 Risk Assessment**: Automated compliance checking and scoring
- **🔒 Enterprise Security**: Multi-tenant architecture with SSO
- **💳 Flexible Billing**: Stripe integration with usage-based pricing
- **📈 Scalable Architecture**: Docker + AWS deployment ready

### Billing Tiers

| Tier | Price | Pages/Month | Features |
|------|-------|-------------|----------|
| **Free** | $0 | 50 | Basic analysis, Q&A |
| **Pro** | $29 | 1,500 | Advanced analysis, comparisons |
| **Enterprise** | $199 | Unlimited | SSO, custom playbooks, priority |

## 📚 Documentation

- **[Setup Guide](SETUP.md)**: Detailed installation instructions
- **[Requirements](/.kiro/specs/lexiscan-ai-contract-analyzer/requirements.md)**: Functional requirements
- **[Design Document](/.kiro/specs/lexiscan-ai-contract-analyzer/design.md)**: Technical architecture
- **[Implementation Tasks](/.kiro/specs/lexiscan-ai-contract-analyzer/tasks.md)**: Development roadmap
- **[AWS Setup](aws-setup/)**: Cloud infrastructure configuration
- **[Stripe Setup](stripe-setup/)**: Billing integration guide

## 🔧 Scripts

| Script | Purpose |
|--------|---------|
| `scripts/verify-prerequisites.sh` | Check system requirements |
| `scripts/init-env.sh` | Initialize environment configuration |
| `aws-setup/setup-aws-resources.sh` | Create AWS infrastructure |

## 🚦 Current Status

**Task 0 Complete**: All prerequisites and environment setup files have been created.

### ✅ Completed
- System requirements verification
- Environment configuration templates
- AWS infrastructure setup scripts
- Stripe webhook configuration guide
- Project documentation structure

### 🔄 Next Steps
1. **Upgrade Node.js** to version 20+ (currently 18.20.8)
2. **Configure API keys** in `.env` file
3. **Start Docker daemon** if needed
4. **Test the development environment**: Run `make setup` to start all services

## 📞 Support

For questions or issues:
1. Check the [Setup Guide](SETUP.md) for detailed instructions
2. Run `./scripts/verify-prerequisites.sh` to diagnose issues
3. Review the requirements and design documents in `.kiro/specs/`

---

**Task 1 Complete**: Project structure and development environment have been set up. Ready to proceed to Task 2: Database foundation and multi-tenancy.