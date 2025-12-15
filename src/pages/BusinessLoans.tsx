import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget, openChatWidget } from '../components/ChatWidget';
import { Building2, Check, TrendingUp, Users } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import { Link } from 'react-router-dom';

export function BusinessLoans() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-amber-500 to-amber-600 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center">
                  <Building2 className="w-8 h-8 text-amber-600" />
                </div>
                <h1 className="text-5xl">Business Loans</h1>
              </div>
              <p className="text-2xl mb-6 opacity-90">
                Fuel your business growth with flexible financing
              </p>
              <div className="flex flex-wrap gap-4">
                <button onClick={openChatWidget} className="bg-white text-amber-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
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
                src="https://images.unsplash.com/photo-1630344745991-fb948c5bf9d1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxidXNpbmVzcyUyMGdyb3d0aCUyMHN1Y2Nlc3N8ZW58MXx8fHwxNzY1MTIxMjk2fDA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Business Loans"
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
            <h2 className="text-3xl text-gray-900 mb-4">Why Choose Our Business Loans?</h2>
            <p className="text-xl text-gray-600">Fast funding, flexible terms, and minimal documentation</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-amber-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Quick Disbursal</h3>
              <p className="text-gray-600">Get funds in your account within 48 hours of approval</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-amber-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">For All Business Types</h3>
              <p className="text-gray-600">MSMEs, startups, and established businesses all welcome</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Building2 className="w-8 h-8 text-amber-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Flexible Repayment</h3>
              <p className="text-gray-600">Choose tenure and EMI that suits your cash flow</p>
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
                  { label: 'Loan Amount', value: '₹5 lakhs to ₹75 lakhs' },
                  { label: 'Interest Rate', value: 'Starting from 11% p.a.' },
                  { label: 'Loan Tenure', value: '12 to 84 months' },
                  { label: 'Processing Fee', value: 'Up to 3% of loan amount' },
                  { label: 'Collateral', value: 'Not required up to ₹10 lakhs' },
                  { label: 'Moratorium Period', value: 'Up to 6 months available' }
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
                  'Business Vintage: Minimum 2 years',
                  'Annual Turnover: Minimum ₹15 lakhs',
                  'Age: 21 to 65 years',
                  'Business Type: Proprietor/Partnership/Pvt Ltd',
                  'CIBIL Score: 650 or above',
                  'ITR: Last 2 years filed'
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-amber-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
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

      {/* Use Cases */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">What Can You Use The Loan For?</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              'Working Capital',
              'Equipment Purchase',
              'Business Expansion',
              'Inventory Purchase',
              'Office Renovation',
              'Marketing Campaigns',
              'Technology Upgrade',
              'Hiring & Training'
            ].map((useCase, index) => (
              <div key={index} className="bg-white rounded-xl shadow-lg p-6 text-center border-2 border-transparent hover:border-amber-500 transition-colors">
                <p className="text-gray-900">{useCase}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Documents Required */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Documents Required</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-gray-50 rounded-xl p-8">
              <h3 className="text-xl text-gray-900 mb-4">KYC Documents</h3>
              <ul className="space-y-3">
                {[
                  'PAN Card',
                  'Aadhaar Card',
                  'Address Proof',
                  'Passport size photo'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-50 rounded-xl p-8">
              <h3 className="text-xl text-gray-900 mb-4">Business Documents</h3>
              <ul className="space-y-3">
                {[
                  'GST Registration',
                  'Business Registration',
                  'Partnership Deed',
                  'MOA/AOA (if Pvt Ltd)'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-50 rounded-xl p-8">
              <h3 className="text-xl text-gray-900 mb-4">Financial Documents</h3>
              <ul className="space-y-3">
                {[
                  'Last 2 years ITR',
                  'Last 6 months bank statement',
                  'Balance Sheet & P&L',
                  'GST Returns'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-amber-500 to-amber-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Ready to Grow Your Business?</h2>
          <p className="text-xl mb-8 opacity-90">
            Get instant approval and competitive rates for your business loan
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <button onClick={openChatWidget} className="bg-white text-amber-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
              Apply for Business Loan
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