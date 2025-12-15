import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget, openChatWidget } from '../components/ChatWidget';
import { Briefcase, Check, Calculator, FileText, Clock, Shield } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import { Link } from 'react-router-dom';

export function PersonalLoans() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-blue-500 to-blue-600 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center">
                  <Briefcase className="w-8 h-8 text-blue-600" />
                </div>
                <h1 className="text-5xl">Personal Loans</h1>
              </div>
              <p className="text-2xl mb-6 opacity-90">
                Quick and hassle-free personal loans for all your needs
              </p>
              <div className="flex flex-wrap gap-4">
                <button onClick={openChatWidget} className="bg-white text-blue-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
                  Apply Now
                </button>
                <Link to="/emi-calculator">
                  <button className="border-2 border-white text-white px-8 py-4 rounded-lg hover:bg-white/10 transition-colors">
                    Calculate EMI
                  </button>
                </Link>
              </div>
            </div>
            <div>
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1635646917531-0806b8abcadd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBwcm9mZXNzaW9uYWwlMjBzbWFydHBob25lJTIwaGFwcHl8ZW58MXx8fHwxNzY1MTc3NTY3fDA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Personal Loans"
                className="w-full h-96 object-cover rounded-xl shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Why Choose Our Personal Loans?</h2>
            <p className="text-xl text-gray-600">Fast approval, flexible terms, and competitive rates</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Clock className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Instant Approval</h3>
              <p className="text-gray-600">Get your loan approved in just 5 minutes with our AI-powered system</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">100% Paperless</h3>
              <p className="text-gray-600">Complete digital process with minimal documentation required</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">No Collateral</h3>
              <p className="text-gray-600">Unsecured loans with no need for guarantor or collateral</p>
            </div>
          </div>
        </div>
      </section>

      {/* Loan Details */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12">
            <div>
              <h2 className="text-3xl text-gray-900 mb-6">Loan Features</h2>
              <div className="space-y-4">
                {[
                  { label: 'Loan Amount', value: '₹50,000 to ₹25 lakhs' },
                  { label: 'Interest Rate', value: 'Starting from 10.5% p.a.' },
                  { label: 'Loan Tenure', value: '12 to 60 months' },
                  { label: 'Processing Fee', value: 'Up to 2.5% of loan amount' },
                  { label: 'Prepayment Charges', value: 'Nil after 6 months' },
                  { label: 'Disbursal Time', value: 'Within 24 hours' }
                ].map((item, index) => (
                  <div key={index} className="flex justify-between items-center bg-gray-50 rounded-lg p-4">
                    <span className="text-gray-700">{item.label}</span>
                    <span className="text-gray-900">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h2 className="text-3xl text-gray-900 mb-6">Eligibility Criteria</h2>
              <div className="space-y-4">
                {[
                  'Age: 21 to 60 years',
                  'Minimum Monthly Income: ₹15,000',
                  'Employment: Salaried or Self-employed',
                  'Work Experience: Minimum 1 year',
                  'CIBIL Score: 650 or above',
                  'Residential Status: Indian Resident'
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-gray-700">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Documents Required */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Documents Required</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-xl text-gray-900 mb-4">For Salaried Individuals</h3>
              <ul className="space-y-3">
                {[
                  'PAN Card',
                  'Aadhaar Card',
                  'Latest 3 months salary slips',
                  'Last 6 months bank statement',
                  'Passport size photograph'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-blue-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-xl text-gray-900 mb-4">For Self-Employed Individuals</h3>
              <ul className="space-y-3">
                {[
                  'PAN Card',
                  'Aadhaar Card',
                  'Business registration proof',
                  'Last 2 years ITR',
                  'Last 6 months bank statement',
                  'Business address proof'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-blue-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-blue-500 to-blue-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Ready to Get Your Personal Loan?</h2>
          <p className="text-xl mb-8 opacity-90">
            Chat with our AI assistant for instant approval in just 5 minutes
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <button className="bg-white text-blue-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors" onClick={openChatWidget}>
              Chat with AI Assistant
            </button>
            <Link to="/emi-calculator">
              <button className="border-2 border-white text-white px-8 py-4 rounded-lg hover:bg-white/10 transition-colors">
                Calculate Your EMI
              </button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
      <ChatWidget />
    </div>
  );
}