import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { EMICalculator } from './pages/EMICalculator';
import { Products } from './pages/Products';
import { PersonalLoans } from './pages/PersonalLoans';
import { HomeLoans } from './pages/HomeLoans';
import { BusinessLoans } from './pages/BusinessLoans';
import { LoanAgainstProperty } from './pages/LoanAgainstProperty';
import { About } from './pages/About';
import { Contact } from './pages/Contact';
import { FAQs } from './pages/FAQs';
import { ProtectedRoute } from './components/ProtectedRoute';

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/emi-calculator" element={<EMICalculator />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/personal-loans" element={<PersonalLoans />} />
          <Route path="/products/home-loans" element={<HomeLoans />} />
          <Route path="/products/business-loans" element={<BusinessLoans />} />
          <Route path="/products/loan-against-property" element={<LoanAgainstProperty />} />
          <Route path="/about" element={<About />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/faqs" element={<FAQs />} />
          
          {/* Login Route */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Admin Dashboard - Public for Demo */}
          <Route
            path="/admin"
            element={<AdminDashboard />}
          />
          
          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}