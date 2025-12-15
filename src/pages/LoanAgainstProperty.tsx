import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget, openChatWidget } from '../components/ChatWidget';
import { Landmark, Check, Home, Building } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import { Link } from 'react-router-dom';

export function LoanAgainstProperty() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-purple-500 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center">
                  <Landmark className="w-8 h-8 text-purple-600" />
                </div>
                <h1 className="text-5xl">Loan Against Property</h1>
              </div>
              <p className="text-2xl mb-6 opacity-90">
                Unlock the value of your property for any need
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <button onClick={openChatWidget} className="bg-white text-purple-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
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
                src="https://images.unsplash.com/photo-1694702740570-0a31ee1525c7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjUwOTExNzN8MA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Loan Against Property"
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
            <h2 className="text-3xl text-gray-900 mb-4">Why Choose Loan Against Property?</h2>
            <p className="text-xl text-gray-600">High loan amount, low interest, and flexible usage</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Landmark className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">High Loan Amount</h3>
              <p className="text-gray-600">Get up to ₹10 crores based on your property value</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Home className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Keep Your Property</h3>
              <p className="text-gray-600">Continue using your property while repaying the loan</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Building className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Multi-Purpose Usage</h3>
              <p className="text-gray-600">Use funds for business, education, medical, or any purpose</p>
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
                  { label: 'Loan Amount', value: 'Up to ₹10 crores' },
                  { label: 'Interest Rate', value: 'Starting from 9.5% p.a.' },
                  { label: 'Loan Tenure', value: 'Up to 20 years' },
                  { label: 'LTV Ratio', value: 'Up to 65% of property value' },
                  { label: 'Processing Fee', value: 'Up to 2% of loan amount' },
                  { label: 'Prepayment Charges', value: 'Nil after 12 months' }
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
                  'Age: 21 to 65 years',
                  'Property: Residential or Commercial',
                  'Property Ownership: Self or co-owned',
                  'Employment: Salaried or Self-employed',
                  'CIBIL Score: 700 or above',
                  'Property: Clear title and marketable'
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
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

      {/* Property Types */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Accepted Property Types</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { type: 'Residential House', desc: 'Independent houses and villas' },
              { type: 'Residential Flat', desc: 'Apartments in approved projects' },
              { type: 'Commercial Property', desc: 'Shops and office spaces' },
              { type: 'Industrial Property', desc: 'Factories and warehouses' }
            ].map((property, index) => (
              <div key={index} className="bg-white rounded-xl shadow-lg p-6 border-2 border-transparent hover:border-purple-500 transition-colors">
                <h3 className="text-lg text-gray-900 mb-2">{property.type}</h3>
                <p className="text-sm text-gray-600">{property.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">How Can You Use The Funds?</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              'Business Expansion',
              'Medical Emergency',
              "Child's Education",
              'Debt Consolidation',
              'Property Purchase',
              'Wedding Expenses',
              'Inventory Purchase',
              'Equipment Purchase',
              'Any Personal Need'
            ].map((useCase, index) => (
              <div key={index} className="bg-gray-50 rounded-xl p-6 flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <Check className="w-5 h-5 text-white" />
                </div>
                <span className="text-gray-900">{useCase}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Documents Required */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Documents Required</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-xl text-gray-900 mb-4">Personal Documents</h3>
              <ul className="space-y-3">
                {[
                  'PAN Card (mandatory)',
                  'Aadhaar Card',
                  'Passport size photographs',
                  'Address proof',
                  'Last 6 months bank statement',
                  'Income proof (salary slips/ITR)'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-purple-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8">
              <h3 className="text-xl text-gray-900 mb-4">Property Documents</h3>
              <ul className="space-y-3">
                {[
                  'Title deed / Sale deed',
                  'Property tax receipts',
                  'Approved building plan',
                  'Encumbrance certificate',
                  'Property valuation report',
                  'NOC from society (if applicable)'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-purple-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-purple-500 to-purple-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Unlock Your Property Value Today</h2>
          <p className="text-xl mb-8 opacity-90">
            Get instant approval and competitive rates on loan against property
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <button className="bg-white text-purple-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
              Apply Now
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