# iVote Systems - Frontend UI

**Modern React.js frontend for secure online voting**

---

## 📋 Overview

The iVS Frontend is a professional, accessible, and secure React application providing:
- User authentication & multi-factor login
- Voter registration with email/SMS verification
- Intuitive ballot interface for vote casting
- Real-time admin dashboard for election monitoring
- Audit log viewer for transparency
- WCAG 2.1 AA accessibility compliance
- Mobile-responsive design

---

## 🚀 Quick Start

### Prerequisites
```bash
Node.js 18+ 
npm 9+ or yarn 3+
```

### Installation

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
# or
yarn install
```

3. **Setup environment**
```bash
cp .env.example .env.local
# Edit .env.local with your API URL and configuration
```

Example `.env.local`:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_VERSION=v1
REACT_APP_JWT_EXPIRY=900
REACT_APP_OTP_RESEND_TIMEOUT=60
```

4. **Run development server**
```bash
npm start
```

The application will open at: `http://localhost:3000`

---

## 📁 Project Structure

```
frontend/
├── public/                 # Static assets
│   ├── index.html         # HTML entry point
│   ├── favicon.ico        # App icon
│   └── manifest.json      # PWA manifest
│
├── src/
│   ├── components/        # Reusable components
│   │   ├── Auth/         # Login, Register, OTP
│   │   ├── Voting/       # Ballot, Vote confirmation
│   │   ├── Admin/        # Dashboard, Election management
│   │   ├── Common/       # Header, Footer, Navigation
│   │   └── Accessibility/ # ARIA labels, keyboard support
│   │
│   ├── pages/            # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── VotingPage.tsx
│   │   ├── AdminDashboard.tsx
│   │   └── ResultsPage.tsx
│   │
│   ├── services/         # API client
│   │   ├── api.ts        # Axios instance
│   │   ├── auth.ts       # Auth API calls
│   │   ├── elections.ts  # Election API calls
│   │   └── voting.ts     # Voting API calls
│   │
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.ts    # Authentication hook
│   │   ├── useVoting.ts  # Voting state management
│   │   └── useWebSocket.ts # Real-time updates
│   │
│   ├── context/          # React Context
│   │   ├── AuthContext.tsx
│   │   ├── ElectionContext.tsx
│   │   └── UIContext.tsx
│   │
│   ├── utils/            # Utilities
│   │   ├── encryption.ts # Client-side encryption
│   │   ├── validators.ts # Input validation
│   │   ├── formatters.ts # Data formatting
│   │   └── storage.ts    # LocalStorage management
│   │
│   ├── styles/           # Global styles
│   │   ├── index.css     # Tailwind imports
│   │   ├── globals.css   # Global styles
│   │   └── accessibility.css # A11y styles
│   │
│   ├── App.tsx           # Root component
│   ├── App.css           # App styles
│   └── index.tsx         # Entry point
│
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript config
├── tailwind.config.js    # Tailwind CSS config
├── jest.config.js        # Jest test config
├── .env.example          # Environment template
└── README.md             # This file
```

---

## 🎨 Key Pages & Components

### Authentication Pages
- **LoginPage**: Email & password login with OTP verification
- **RegisterPage**: Multi-step voter registration
- **ForgotPasswordPage**: Password recovery flow

### Voter Pages
- **VotingDashboard**: List available elections
- **BallotPage**: Candidate selection & vote casting
- **VoteConfirmation**: Receipt & confirmation
- **ResultsPage**: Election results & statistics

### Admin Pages
- **AdminDashboard**: Overview & statistics
- **ElectionManagement**: Create/edit elections
- **VoterApproval**: Queue of pending voters
- **LiveResults**: Real-time vote tallying
- **AuditLog**: Transparency & accountability

---

## 🔐 Security Features

### Client-Side Security
- **JWT Token Storage**: Secure token management
- **XSS Protection**: Input validation & output encoding
- **CSRF Prevention**: Token-based CSRF protection
- **Encryption**: AES-256 vote encryption before transmission
- **Secure Session**: Auto-logout after inactivity

### API Integration
- **HTTPS Only**: All API calls use HTTPS/TLS 1.3
- **Request Validation**: Client-side validation before API calls
- **Error Handling**: Secure error messages (no sensitive data)
- **Rate Limiting**: Client-side throttling

---

## 📦 Key Dependencies

```json
{
  "react": "^18.2.0",
  "react-router-dom": "^6.16.0",
  "typescript": "^5.2.0",
  "axios": "^1.5.0",
  "crypto-js": "^4.1.1",
  "zustand": "^4.4.0",
  "react-i18next": "^13.2.0",
  "tailwindcss": "^3.3.0",
  "autoprefixer": "^10.4.0",
  "postcss": "^8.4.0",
  "recharts": "^2.10.0",
  "react-hook-form": "^7.48.0"
}
```

---

## 🧪 Testing

### Run all tests
```bash
npm test
```

### Run with coverage
```bash
npm test -- --coverage
```

### Watch mode
```bash
npm test -- --watch
```

### E2E tests with Cypress
```bash
npm run cypress:open    # Interactive
npm run cypress:run     # Headless
```

---

## 🌐 Internationalization (i18n)

### Supported Languages
- English (en)
- Swahili (sw)
- French (fr)

### Adding new language
1. Create translation file: `src/i18n/locales/[lang].json`
2. Add language to `i18n.config.ts`
3. Test with lang selector

---

## ♿ Accessibility (A11y)

### Compliance Level
- **WCAG 2.1 Level AA**
- **Section 508 compliant**

### Features
- Semantic HTML5
- ARIA labels & descriptions
- Keyboard navigation (Tab, Enter, Escape)
- Focus indicators
- High contrast support
- Screen reader compatible
- Color-blind friendly

### Testing A11y
```bash
npm run a11y-check
# Uses axe-core & jest-axe
```

---

## 📱 Responsive Design

### Breakpoints
```css
Mobile:     < 640px
Tablet:     640px - 1024px
Desktop:    > 1024px
```

### Mobile Optimization
- Touch-friendly buttons (48px min)
- Readable font sizes
- Optimized form inputs
- Offline support via Service Worker

---

## 🚀 Build & Deployment

### Production Build
```bash
npm run build
# Creates optimized build in `build/` folder
```

### Serve production build locally
```bash
npm install -g serve
serve -s build
```

### Environment-specific builds
```bash
# Development
npm run build:dev

# Staging
npm run build:staging

# Production
npm run build:prod
```

### Deploy to Vercel
```bash
npm i -g vercel
vercel
```

### Deploy to Netlify
```bash
npm run build
# Drag & drop `build/` folder to Netlify
```

---

## 🔄 Real-Time Updates

### WebSocket Integration
- Live election status updates
- Real-time vote counts (aggregated)
- Admin notifications
- Live chat for support

```typescript
import { useWebSocket } from './hooks/useWebSocket';

const { data, isConnected } = useWebSocket('wss://api.example.com/ws/election/1/');
```

---

## 🎨 Styling

### Tailwind CSS
- Utility-first CSS framework
- Pre-configured for accessibility
- Mobile-first responsive design

### Custom Theme
Edit `tailwind.config.js` for:
- Colors (primary, secondary, danger, success)
- Typography (fonts, sizes)
- Spacing
- Shadows & borders

---

## 📊 State Management

### Context API + Zustand
- AuthContext: User authentication & profile
- ElectionContext: Current election data
- VotingContext: Vote submission state
- UIContext: UI theme & notifications

---

## 🐛 Troubleshooting

### Port already in use
```bash
# Find process
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
PORT=3001 npm start
```

### Clear cache
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### API connection issues
- Check `REACT_APP_API_URL` in `.env.local`
- Verify backend is running on port 8000
- Check CORS configuration in backend

### TypeScript errors
```bash
# Force TypeScript recompile
rm -rf build
npm run build
```

---

## 📚 Additional Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [React Router](https://reactrouter.com/)
- [Web Accessibility (WCAG)](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Version**: 0.1.0  
**Last Updated**: January 15, 2026
