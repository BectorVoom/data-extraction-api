# Data Extraction Frontend

A modern, responsive frontend built with Svelte 5, TypeScript, and Tailwind CSS for querying the Data Extraction API. Features real-time validation, error handling, and an intuitive user interface.

## Features

- **Svelte 5**: Modern reactive framework with runes and enhanced TypeScript support
- **TypeScript**: Full type safety for robust development experience
- **Tailwind CSS**: utility-first CSS framework for responsive design
- **Real-time Validation**: Client-side validation with immediate feedback
- **API Integration**: Type-safe communication with the FastAPI backend
- **Error Handling**: User-friendly error messages and loading states
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Accessible UI**: WCAG-compliant form elements and interactions

## Requirements

- Node.js 18+ or Bun
- Backend API running on `http://localhost:8000`

## Installation

1. **Navigate to frontend directory**:
   ```bash
   cd frontend_svelte_tailwindcss
   ```

2. **Install dependencies with Bun**:
   ```bash
   bun install
   ```

## Running the Application

### Development Mode

```bash
bun run dev
```

The frontend will start on `http://localhost:5173` with hot module replacement.

### Build for Production

```bash
bun run build
```

### Preview Production Build

```bash
bun run preview
```

## Features Overview

### Query Form
- **ID Input**: Accepts string or numeric identifiers
- **Date Range Selection**: HTML5 date inputs with yyyy/mm/dd validation
- **Real-time Validation**: Immediate feedback on input errors
- **Submit States**: Loading indicators and disabled states during requests

### Results Display
- **Responsive Table**: Displays query results in a clean, sortable format
- **Data Formatting**: Currency formatting, date formatting, and status badges
- **Empty States**: User-friendly messages when no results are found
- **Error Handling**: Clear error messages for API failures

### Validation Rules

#### Client-Side Validation
- **Date Format**: Enforces yyyy/mm/dd format
- **Date Range**: Ensures fromDate ≤ toDate
- **Required Fields**: All fields must be completed
- **Real-time Feedback**: Validation occurs as user types

#### Server-Side Integration
- Handles backend validation errors gracefully
- Displays detailed error messages from API
- Maintains form state during error conditions

## Project Structure

```
frontend_svelte_tailwindcss/
├── src/
│   ├── lib/
│   │   ├── types.ts           # TypeScript interfaces
│   │   ├── api.ts             # API service layer
│   │   ├── validation.ts      # Client-side validation
│   │   ├── QueryForm.svelte   # Main query form component
│   │   └── ResultsTable.svelte # Results display component
│   ├── App.svelte             # Root application component
│   ├── main.ts               # Application entry point
│   └── app.css               # Tailwind CSS imports
├── public/
├── package.json
├── tailwind.config.js         # Tailwind configuration
├── tsconfig.json             # TypeScript configuration
└── vite.config.ts            # Vite configuration
```

## API Integration

The frontend communicates with the backend API using a type-safe service layer:

### API Service (`src/lib/api.ts`)
- Singleton pattern for consistent API access
- Environment-aware base URL configuration
- Comprehensive error handling
- TypeScript interfaces for all requests/responses

### Request Example
```typescript
const response = await apiService.queryData({
  id: "12345",
  fromDate: "2024/01/01",
  toDate: "2024/12/31"
});
```

## Environment Configuration

Create a `.env` file for custom API endpoint:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Development Workflow

### Type Safety
- All API responses are typed with TypeScript interfaces
- Compile-time validation prevents runtime errors
- IntelliSense support throughout the codebase

### Component Architecture
- **QueryForm**: Main form component with validation and submission logic
- **ResultsTable**: Reusable table component with formatting and empty states
- **App**: Root component managing global state and event handling

### Styling Approach
- Tailwind CSS utility classes for responsive design
- Component-scoped styling where needed
- Consistent design system with proper spacing and colors
- Dark mode compatible color scheme

## User Experience Features

### Form Interaction
- **Auto-focus**: Cursor automatically moves to first field
- **Tab Navigation**: Proper tab order for accessibility
- **Enter Submission**: Form can be submitted with Enter key
- **Loading States**: Visual feedback during API requests

### Error Handling
- **Validation Errors**: Inline validation with red styling
- **API Errors**: Toast-style error messages
- **Network Errors**: Graceful handling of connection issues
- **Recovery**: Easy form reset and retry functionality

### Responsive Design
- **Mobile-First**: Optimized for mobile devices
- **Desktop Enhancement**: Full-width layout on larger screens
- **Touch-Friendly**: Large tap targets for mobile interaction
- **Keyboard Navigation**: Full keyboard support

## Testing

### Component Testing
Components can be tested using Vitest and Testing Library:

```bash
bun run test
```

### Type Checking
Verify TypeScript compilation:

```bash
bun run check
```

## Browser Support

- Modern browsers supporting ES2020
- Mobile browsers (iOS Safari, Chrome Mobile)
- Progressive enhancement for older browsers

## Performance

### Build Optimization
- Tree-shaking eliminates unused code
- CSS purging removes unused Tailwind classes
- Bundle splitting for optimal loading
- Compression and minification in production

### Runtime Performance
- Svelte's compile-time optimizations
- Minimal JavaScript bundle size
- Efficient DOM updates with Svelte's reactivity
- Optimized API request handling

## Deployment

### Static Hosting
The built application is a static site that can be deployed to:
- Vercel
- Netlify  
- GitHub Pages
- Any static file server

### Environment Variables
Configure the API base URL for different environments:
- Development: `http://localhost:8000`
- Production: Your production API endpoint

## Development Notes

### Tailwind CSS Configuration
- Configured to scan all Svelte files for utility classes
- Custom color palette for consistent theming
- Responsive breakpoints for mobile-first design

### Vite Configuration
- Optimized for Svelte development
- Hot module replacement for fast development
- TypeScript support with type checking

### Code Quality
- TypeScript strict mode enabled
- Consistent formatting and linting
- Component props validation
- Comprehensive error boundaries

## License

This project is part of a technical implementation demonstrating modern frontend development with Svelte, TypeScript, and Tailwind CSS.