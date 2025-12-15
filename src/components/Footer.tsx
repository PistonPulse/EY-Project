import { Link } from 'react-router-dom';
import { Facebook, Twitter, Linkedin, Youtube, Mail, Phone, MapPin } from 'lucide-react';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";

export function Footer() {
  return (
    <footer className="bg-[#004589] text-white">
      {/* Main Footer Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-6 sm:gap-8 mb-6 sm:mb-8">
          {/* Company Info */}
          <div className="sm:col-span-2 md:col-span-2">
            <div className="bg-white rounded-lg p-2 inline-block mb-3 sm:mb-4">
              <img src={tataLogo} alt="Tata Capital" className="h-8 sm:h-10 object-contain" />
            </div>
            <p className="text-sm sm:text-base text-blue-100 mb-3 sm:mb-4">
              Tata Capital is a leading financial services provider, offering comprehensive and
              innovative financial solutions to corporate and retail customers.
            </p>
            <div className="inline-block bg-yellow-400 text-[#004589] px-3 py-1 text-xs sm:text-sm font-semibold">
              Part of the Tata Group
            </div>
          </div>

          {/* Products */}
          <div>
            <h4 className="mb-3 sm:mb-4 font-semibold text-base sm:text-lg">Products</h4>
            <ul className="space-y-2 text-xs sm:text-sm text-blue-100">
              <li>
                <Link to="/products/personal-loans" className="hover:text-white transition-colors">
                  Personal Loans
                </Link>
              </li>
              <li>
                <Link to="/products/home-loans" className="hover:text-white transition-colors">
                  Home Loans
                </Link>
              </li>
              <li>
                <Link to="/products/business-loans" className="hover:text-white transition-colors">
                  Business Loans
                </Link>
              </li>
              <li>
                <Link to="/products/loan-against-property" className="hover:text-white transition-colors">
                  Loan Against Property
                </Link>
              </li>
              <li>
                <Link to="/products" className="hover:text-white transition-colors">
                  View All Products
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="mb-3 sm:mb-4 font-semibold text-base sm:text-lg">Resources</h4>
            <ul className="space-y-2 text-xs sm:text-sm text-blue-100">
              <li>
                <Link to="/emi-calculator" className="hover:text-white transition-colors">
                  EMI Calculator
                </Link>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Branch Locator
                </a>
              </li>
              <li>
                <Link to="/faqs" className="hover:text-white transition-colors">
                  FAQs
                </Link>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Grievance Redressal
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Financial Calculators
                </a>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="mb-3 sm:mb-4 font-semibold text-base sm:text-lg">Company</h4>
            <ul className="space-y-2 text-xs sm:text-sm text-blue-100">
              <li>
                <Link to="/about" className="hover:text-white transition-colors">
                  About Us
                </Link>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Careers
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Investor Relations
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-white transition-colors">
                  Press & Media
                </a>
              </li>
              <li>
                <Link to="/contact" className="hover:text-white transition-colors">
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Contact Info */}
        <div className="border-t border-blue-400/30 pt-6 sm:pt-8 mb-6 sm:mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
            <div className="flex items-start gap-3">
              <Phone className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-400 flex-shrink-0 mt-1" />
              <div>
                <div className="text-xs sm:text-sm text-blue-100">Customer Care</div>
                <div className="text-sm sm:text-base font-semibold">1800-209-8800</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Mail className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-400 flex-shrink-0 mt-1" />
              <div>
                <div className="text-xs sm:text-sm text-blue-100">Email</div>
                <div className="text-sm sm:text-base break-all">customersupport@tatacapital.com</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <MapPin className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-400 flex-shrink-0 mt-1" />
              <div>
                <div className="text-xs sm:text-sm text-blue-100">Head Office</div>
                <div className="text-sm sm:text-base">Mumbai, Maharashtra, India</div>
              </div>
            </div>
          </div>
        </div>

        {/* Social Media & Legal */}
        <div className="border-t border-blue-400/30 pt-6 sm:pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            {/* Social Media */}
            <div className="flex items-center gap-3 sm:gap-4">
              <span className="text-xs sm:text-sm text-blue-100">Follow Us:</span>
              <a
                href="https://www.facebook.com/TataCapital"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Facebook className="w-5 h-5" />
              </a>
              <a
                href="https://twitter.com/TataCapital"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Twitter className="w-5 h-5" />
              </a>
              <a
                href="https://www.linkedin.com/company/tata-capital"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Linkedin className="w-5 h-5" />
              </a>
              <a
                href="https://www.youtube.com/user/TataCapitalLimited"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 bg-white/10 rounded-full flex items-center justify-center hover:bg-white/20 transition-colors"
              >
                <Youtube className="w-5 h-5" />
              </a>
            </div>

            {/* Legal Links */}
            <div className="flex flex-wrap items-center gap-4 text-sm text-blue-100">
              <a href="#" className="hover:text-white transition-colors">
                Privacy Policy
              </a>
              <span>|</span>
              <a href="#" className="hover:text-white transition-colors">
                Terms & Conditions
              </a>
              <span>|</span>
              <a href="#" className="hover:text-white transition-colors">
                Fair Practices Code
              </a>
              <span>|</span>
              <a href="#" className="hover:text-white transition-colors">
                Disclaimer
              </a>
            </div>
          </div>
        </div>

        {/* Copyright & Disclaimer */}
        <div className="border-t border-blue-400/30 mt-8 pt-8 text-center text-sm text-blue-100">
          <p className="mb-2">
            © 2025 Tata Capital Limited. All rights reserved. CIN: U65923MH1991PLC060670
          </p>
          <p className="text-xs">
            Tata Capital Limited is registered with the Reserve Bank of India (RBI) as a
            Non-Banking Financial Company (NBFC). This is a demo application developed for the EY
            Techathon 2025.
          </p>
        </div>
      </div>
    </footer>
  );
}