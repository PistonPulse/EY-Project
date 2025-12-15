import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget, openChatWidget } from '../components/ChatWidget';
import { Home, Check, TrendingDown, Award } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import { Link } from 'react-router-dom';

export function HomeLoans() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-green-500 to-green-600 text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center">
                  <Home className="w-8 h-8 text-green-600" />
                </div>
                <h1 className="text-5xl">Home Loans</h1>
              </div>
              <p className="text-2xl mb-6 opacity-90">
                Make your dream of owning a home come true
              </p>
              <div className="flex flex-wrap gap-4">
                <button onClick={openChatWidget} className="bg-white text-green-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
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
                src="https://images.unsplash.com/photo-1730130596425-197566414dc4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBmYW1pbHklMjBob21lfGVufDF8fHx8MTc2NTE3OTI4OXww&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Home Loans"
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
            <h2 className="text-3xl text-gray-900 mb-4">Home Loan Benefits</h2>
            <p className="text-xl text-gray-600">Affordable rates, long tenure, and tax benefits</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingDown className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Low Interest Rates</h3>
              <p className="text-gray-600">Starting from 8.5% p.a. - among the lowest in the market</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Award className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">Tax Benefits</h3>
              <p className="text-gray-600">Save up to ₹3.5 lakhs annually under Section 80C & 24</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Home className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-3">High Loan Amount</h3>
              <p className="text-gray-600">Get up to ₹10 crores for your dream home</p>
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
                  { label: 'Interest Rate', value: 'Starting from 8.5% p.a.' },
                  { label: 'Loan Tenure', value: 'Up to 30 years' },
                  { label: 'Processing Fee', value: 'Up to 1% of loan amount' },
                  { label: 'Part Payment', value: 'Allowed after 6 months' },
                  { label: 'LTV Ratio', value: 'Up to 90% of property value' }
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
                  'Minimum Annual Income: ₹3 lakhs',
                  'Employment: Salaried or Self-employed',
                  'Work Experience: Minimum 2 years',
                  'CIBIL Score: 700 or above',
                  'Property: Ready or under-construction'
                ].map((item, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
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

      {/* Types of Home Loans */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Types of Home Loans We Offer</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: 'Home Purchase Loan', desc: 'For buying your new home' },
              { title: 'Home Construction Loan', desc: 'For building your dream house' },
              { title: 'Home Extension Loan', desc: 'For renovating or extending' },
              { title: 'Plot Purchase Loan', desc: 'For buying residential land' },
              { title: 'Balance Transfer', desc: 'Transfer from another lender' },
              { title: 'Top-up Loan', desc: 'Additional loan on existing home loan' }
            ].map((type, index) => (
              <div key={index} className="bg-white rounded-xl shadow-lg p-6 border-2 border-transparent hover:border-green-500 transition-colors">
                <h3 className="text-xl text-gray-900 mb-2">{type.title}</h3>
                <p className="text-gray-600">{type.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Documents Required */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl text-gray-900 mb-8 text-center">Documents Required</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-gray-50 rounded-xl p-8">
              <h3 className="text-xl text-gray-900 mb-4">Identity & Address Proof</h3>
              <ul className="space-y-3">
                {[
                  'PAN Card (mandatory)',
                  'Aadhaar Card',
                  'Passport',
                  'Voter ID',
                  'Driving License'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-50 rounded-xl p-8">
              <h3 className="text-xl text-gray-900 mb-4">Income & Property Documents</h3>
              <ul className="space-y-3">
                {[
                  'Last 6 months salary slips',
                  'Last 2 years ITR',
                  'Bank statements (6 months)',
                  'Property documents',
                  'Sale agreement',
                  'Property tax receipts'
                ].map((doc, index) => (
                  <li key={index} className="flex items-center gap-3">
                    <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <span className="text-gray-700">{doc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-green-500 to-green-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Turn Your Home Dreams Into Reality</h2>
          <p className="text-xl mb-8 opacity-90">
            Get instant pre-approval and best rates with our AI loan assistant
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <button onClick={openChatWidget} className="bg-white text-green-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
              Apply for Home Loan
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