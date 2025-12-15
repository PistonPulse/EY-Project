import { Link } from 'react-router-dom';
import { ChevronDown, Menu, X } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [productsOpen, setProductsOpen] = useState(false);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setProductsOpen(true);
  };

  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setProductsOpen(false);
    }, 300); // 300ms delay before closing
  };

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" onClick={scrollToTop} className="flex items-center hover:opacity-80 transition-opacity">
            <img src={tataLogo} alt="Tata Capital" className="h-8 sm:h-10 object-contain" />
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-8">
            {/* Products Dropdown */}
            <div 
              className="relative"
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
            >
              <button
                className="flex items-center gap-1 text-gray-700 hover:text-[#004589] transition-colors"
              >
                Products
                <ChevronDown className="w-4 h-4" />
              </button>
              
              {productsOpen && (
                <div
                  className="absolute top-full left-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 py-2"
                >
                  <Link
                    to="/products/personal-loans"
                    onClick={scrollToTop}
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 hover:text-[#004589] transition-colors"
                  >
                    Personal Loans
                  </Link>
                  <Link
                    to="/products/home-loans"
                    onClick={scrollToTop}
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 hover:text-[#004589] transition-colors"
                  >
                    Home Loans
                  </Link>
                  <Link
                    to="/products/business-loans"
                    onClick={scrollToTop}
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 hover:text-[#004589] transition-colors"
                  >
                    Business Loans
                  </Link>
                  <Link
                    to="/products/loan-against-property"
                    onClick={scrollToTop}
                    className="block px-4 py-2 text-gray-700 hover:bg-gray-50 hover:text-[#004589] transition-colors"
                  >
                    Loan Against Property
                  </Link>
                </div>
              )}
            </div>

            <Link to="/emi-calculator" onClick={scrollToTop} className="text-gray-700 hover:text-[#004589] transition-colors">
              EMI Calculator
            </Link>
            <Link to="/about" onClick={scrollToTop} className="text-gray-700 hover:text-[#004589] transition-colors">
              About Us
            </Link>
            <Link to="/contact" onClick={scrollToTop} className="text-gray-700 hover:text-[#004589] transition-colors">
              Contact
            </Link>
            <Link to="/faqs" onClick={scrollToTop} className="text-gray-700 hover:text-[#004589] transition-colors">
              FAQs
            </Link>
          </div>

          {/* RCU Login Button */}
          <div className="flex items-center gap-4">
            <Link
              to="/login"
              onClick={scrollToTop}
              className="hidden lg:block px-6 py-2 border border-[#004589] text-[#004589] rounded-lg hover:bg-[#004589] hover:text-white transition-colors font-semibold"
            >
              RCU Login
            </Link>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden text-gray-700 hover:text-[#004589]"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden mt-4 pb-4 border-t border-gray-200 pt-4 bg-white">
            <div className="space-y-1">
              <Link
                to="/products"
                className="block py-3 px-2 text-gray-700 hover:text-[#004589] hover:bg-blue-50 rounded-lg transition-colors"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                Products
              </Link>
              <Link
                to="/emi-calculator"
                className="block py-3 px-2 text-gray-700 hover:text-[#004589] hover:bg-blue-50 rounded-lg transition-colors"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                EMI Calculator
              </Link>
              <Link
                to="/about"
                className="block py-3 px-2 text-gray-700 hover:text-[#004589] hover:bg-blue-50 rounded-lg transition-colors"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                About Us
              </Link>
              <Link
                to="/contact"
                className="block py-3 px-2 text-gray-700 hover:text-[#004589] hover:bg-blue-50 rounded-lg transition-colors"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                Contact
              </Link>
              <Link
                to="/faqs"
                className="block py-3 px-2 text-gray-700 hover:text-[#004589] hover:bg-blue-50 rounded-lg transition-colors"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                FAQs
              </Link>
              <Link
                to="/login"
                className="block py-3 px-2 mt-2 bg-[#004589] text-white text-center rounded-lg hover:bg-[#003366] transition-colors font-semibold"
                onClick={() => { setMobileMenuOpen(false); scrollToTop(); }}
              >
                RCU Login
              </Link>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}