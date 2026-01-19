# iVote Systems (iVS)

**A Secure, Modern, Professional Online Voting Platform**

> Transforming democracy through technology - Building transparent, efficient, and accessible institutional elections.

---

## 📋 Project Structure

```
Online-Voting-System/
├── backend/                    # Django Backend Application
│   ├── ivs_backend/           # Django Project Configuration
│   │   ├── settings.py        # Settings with security & production configs
│   │   ├── urls.py            # Main URL routing
│   │   ├── asgi.py            # ASGI config for WebSockets
│   │   └── wsgi.py            # WSGI config for production
│   ├── accounts/              # User Authentication & Management
│   ├── elections/             # Election Management
│   ├── voting/                # Vote Casting & Encryption
│   ├── auditing/              # Audit Logging & Transparency
│   ├── manage.py              # Django management script
│   ├── requirements.txt        # Python dependencies
│   └── .env                   # Environment variables
│
├── frontend/                   # React Frontend Application
│   ├── public/                # Static public assets
│   ├── src/                   # React source code
│   │   ├── components/        # Reusable React components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API client services
│   │   ├── hooks/             # Custom React hooks
│   │   ├── context/           # React Context for state
│   │   ├── utils/             # Utility functions
│   │   ├── styles/            # Tailwind & CSS
│   │   └── App.tsx            # Root app component
│   ├── package.json           # Node dependencies
│   └── .env.local             # Frontend environment variables
│
├── .git/                       # Git repository
├── .vscode/                    # VS Code settings
└── README.md                   # This file
```

---

## 🎯 Key Features

### Security
- ✅ End-to-end encryption (AES-256) of all votes
- ✅ Multi-factor authentication (OTP + Biometric)
- ✅ JWT token-based authentication
- ✅ Role-based access control (RBAC)
- ✅ Rate limiting & brute-force protection
- ✅ OWASP Top 10 protection

### Core Functionality
- ✅ Secure voter registration & verification
- ✅ Encrypted vote casting & storage
- ✅ Real-time vote tallying (aggregated, no premature decryption)
- ✅ Admin dashboard with live monitoring
- ✅ Audit logging with hash chaining
- ✅ Immutable result records

### User Experience
- ✅ Mobile-responsive React UI
- ✅ WCAG 2.1 AA accessibility compliance
- ✅ Multi-language support (i18n)
- ✅ Progressive enhancement for low-bandwidth
- ✅ Intuitive interface for all user types

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React + TypeScript + Tailwind CSS | Modern, responsive UI |
| **Backend** | Django + Django REST Framework | Secure API & business logic |
| **Database** | PostgreSQL | Encrypted, structured data storage |
| **Auth** | JWT + OTP (Twilio/Email) | Multi-factor authentication |
| **Encryption** | AES-256 + TLS 1.3 | Vote confidentiality |
| **Real-time** | Django Channels (WebSocket) | Live updates |
| **Testing** | pytest, Jest, Cypress | Comprehensive test coverage |
| **Deployment** | Docker + GitHub Actions | CI/CD pipeline |

---

## 📦 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+
- Git

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Backend API will be available at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API URL

# Run development server
npm start
```

Frontend will be available at: `http://localhost:3000`

---

## 📚 Documentation

### For Developers
- [Backend API Documentation](./backend/README.md)
- [Frontend Setup Guide](./frontend/README.md)
- [Architecture Overview](./docs/ARCHITECTURE.md)
- [Security Guidelines](./docs/SECURITY.md)
- [**Email Configuration Guide**](./docs/EMAIL_CONFIGURATION.md) ⭐ **NEW**
- [**Email Enhancement Summary**](./docs/EMAIL_ENHANCEMENT_SUMMARY.md) ⭐ **NEW**

### For Users
- [Voter Guide](./docs/VOTER_GUIDE.md)
- [Admin Guide](./docs/ADMIN_GUIDE.md)

### For Examiners/Reviewers
- [Project Scope & Objectives](./docs/PROJECT_SCOPE.md)
- [Implementation Phases](./docs/IMPLEMENTATION_PHASES.md)
- [Testing Report](./docs/TESTING_REPORT.md)

---

## 🔐 Security Highlights

- **Encrypted Voting**: All votes encrypted with AES-256
- **Voter Authentication**: Multi-factor (Password + OTP + optional Biometric)
- **One-Vote Enforcement**: Cryptographic tokens prevent double voting
- **Audit Trail**: Immutable append-only logs with timestamps & digital signatures
- **Session Security**: Auto-logout after 15 minutes of inactivity
- **HTTPS/TLS 1.3**: All communication encrypted in transit
- **Input Validation**: All inputs sanitized & validated on both client & server

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest -v --cov=.
```

### Frontend Tests
```bash
cd frontend
npm test -- --coverage
```

### E2E Tests
```bash
npm run e2e
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend (3000)                 │
│  (Login, Registration, Voting, Admin Dashboard)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTPS/TLS 1.3
                     │
┌────────────────────▼────────────────────────────────────┐
│              Django REST API (8000)                      │
│  ┌──────────┬──────────┬──────────┬──────────┐          │
│  │ Accounts │Elections │ Voting   │ Auditing │          │
│  └──────────┴──────────┴──────────┴──────────┘          │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐        ┌────────▼──────┐
│ PostgreSQL   │        │ Redis Cache   │
│ (Encrypted)  │        │ (Sessions)    │
└──────────────┘        └───────────────┘
```

---

## 🎯 Implementation Phases

1. **Phase 0**: Project Setup & Infrastructure ✓
2. **Phase 1**: Authentication & Security Foundation
3. **Phase 2**: Voter Registration Module
4. **Phase 3**: Core Voting Engine & Encryption
5. **Phase 4**: Admin Dashboard & Monitoring
6. **Phase 5**: Vote Tallying & Results
7. **Phase 6**: Audit Logging & Transparency
8. **Phase 7**: Accessibility & UI/UX
9. **Phase 8**: Security Hardening
10. **Phase 9**: Testing (Unit/Integration/E2E)
11. **Phase 10**: Performance Optimization
12. **Phase 11**: Deployment & Infrastructure
13. **Phase 12**: Documentation & Knowledge Transfer
14. **Phase 13**: Final Review & Submission

---

## 📝 License

This project is developed for academic and institutional use. See [LICENSE](./LICENSE) for details.

---

## 👥 Contributors

- **Development Team**: iVote Systems Development Team
- **Supervisor**: [Your Supervisor Name]
- **Institution**: [Your Institution]

---

## 📧 Support & Contact

For questions, issues, or feedback:
- Create an issue on GitHub
- Email: support@ivotesystems.org
- Documentation: https://docs.ivotesystems.org

---

**Last Updated**: January 15, 2026  
**Version**: 0.1.0 (Development)