import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget, openChatWidget } from '../components/ChatWidget';
import { Zap, FileText, Percent, Shield, Clock, Award, TrendingUp, Users, Briefcase, Home, Building2, Car } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <AIChatBanner />
      
      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left Side - Content */}
            <div>
              <div className="inline-block bg-blue-100 text-[#004589] px-4 py-2 rounded-full mb-4">
                ✨ Powered by AI
              </div>
              <h1 className="text-5xl font-bold mb-6 text-gray-900 leading-tight">
                Instant Personal Loans at 10.5% APR
              </h1>
              <p className="text-xl text-gray-600 mb-8">
                Get approved in 5 minutes by our new AI Agent. Zero paperwork, instant disbursal.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <button className="bg-[#3B82F6] text-white px-8 py-4 rounded-lg hover:bg-[#2563EB] transition-colors text-base font-semibold">
                  Check Eligibility Now
                </button>
                <button className="border-2 border-[#004589] text-[#004589] px-8 py-4 rounded-lg hover:bg-[#004589] hover:text-white transition-colors text-base font-semibold">
                  Calculate EMI
                </button>
              </div>
              
              {/* Trust Indicators */}
              <div className="flex flex-wrap items-center gap-6 text-base text-gray-600">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-green-600" />
                  <span>100% Secure</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
                  <span>5-Min Approval</span>
                </div>
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 sm:w-5 sm:h-5 text-amber-600" />
                  <span>Tata Trust</span>
                </div>
              </div>
            </div>
            
            {/* Right Side - Image */}
            <div className="relative mt-8 md:mt-0">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1635646917531-0806b8abcadd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBwcm9mZXNzaW9uYWwlMjBzbWFydHBob25lJTIwaGFwcHl8ZW58MXx8fHwxNzY1MTc3NTY3fDA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Happy professional using smartphone"
                className="w-full h-auto rounded-lg shadow-2xl"
              />
              
              {/* Floating Stats */}
              <div className="absolute -bottom-6 -left-6 bg-white rounded-xl shadow-xl p-4 border border-gray-100">
                <div className="text-4xl font-bold text-[#004589] mb-1">₹50K+</div>
                <div className="text-sm text-gray-600">Loans Disbursed</div>
              </div>
              
              <div className="absolute -top-6 -right-6 bg-white rounded-xl shadow-xl p-4 border border-gray-100">
                <div className="text-4xl font-bold text-green-600 mb-1">4.9★</div>
                <div className="text-sm text-gray-600">Customer Rating</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Why Choose Tata Capital?</h2>
            <p className="text-xl text-gray-600">Fast, transparent, and customer-friendly loan process</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="w-14 h-14 bg-[#3B82F6] rounded-xl flex items-center justify-center mb-4">
                <Zap className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">Instant Approval</h3>
              <p className="text-base text-gray-600 leading-relaxed">Our AI agent processes your application in real-time. Get funds in your account within 5 minutes of approval.</p>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="w-14 h-14 bg-[#3B82F6] rounded-xl flex items-center justify-center mb-4">
                <FileText className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">100% Paperless</h3>
              <p className="text-base text-gray-600 leading-relaxed">No physical documents required. Complete verification happens digitally with your PAN and Aadhaar.</p>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow">
              <div className="w-14 h-14 bg-[#3B82F6] rounded-xl flex items-center justify-center mb-4">
                <Percent className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">Low Interest Rates</h3>
              <p className="text-base text-gray-600 leading-relaxed">Starting from 10.5% p.a. for prime customers. Flexible tenure from 12 to 60 months.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Products Section */}
      <section className="py-16 px-6 bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Our Products</h2>
            <p className="text-xl text-gray-600">Comprehensive financial solutions for all your needs</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Personal Loans */}
            <div className="bg-white p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4">
                <Briefcase className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-gray-900">Personal Loans</h3>
              <p className="text-base text-gray-600 mb-4">Quick funds for any personal need. Starting from 10.5% p.a.</p>
              <ul className="space-y-2 text-base text-gray-600 mb-6">
                <li>• Up to ₹25 lakhs</li>
                <li>• Tenure: 12-60 months</li>
                <li>• Minimal documentation</li>
              </ul>
              <button 
                onClick={openChatWidget}
                className="w-full bg-[#004589] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors text-base font-semibold"
              >
                Apply Now
              </button>
            </div>

            {/* Home Loans */}
            <div className="bg-white p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-4">
                <Home className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-gray-900">Home Loans</h3>
              <p className="text-base text-gray-600 mb-4">Make your dream home a reality with attractive rates.</p>
              <ul className="space-y-2 text-base text-gray-600 mb-6">
                <li>• Up to ₹10 crores</li>
                <li>• Tenure: Up to 30 years</li>
                <li>• Tax benefits available</li>
              </ul>
              <button 
                onClick={openChatWidget}
                className="w-full bg-[#004589] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors text-base font-semibold"
              >
                Apply Now
              </button>
            </div>

            {/* Business Loans */}
            <div className="bg-white p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-100">
              <div className="w-16 h-16 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center mb-4">
                <Building2 className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-gray-900">Business Loans</h3>
              <p className="text-base text-gray-600 mb-4">Fuel your business growth with flexible financing.</p>
              <ul className="space-y-2 text-base text-gray-600 mb-6">
                <li>• Up to ₹75 lakhs</li>
                <li>• Flexible repayment</li>
                <li>• Quick processing</li>
              </ul>
              <button 
                onClick={openChatWidget}
                className="w-full bg-[#004589] text-white py-3 rounded-lg hover:bg-[#003366] transition-colors text-base font-semibold"
              >
                Apply Now
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-xl text-gray-600">Get your loan in 3 simple steps</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-20 h-20 bg-[#3B82F6] text-white rounded-full flex items-center justify-center mx-auto mb-4 text-3xl font-bold">
                1
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">Chat with AI</h3>
              <p className="text-base text-gray-600 leading-relaxed">Tell our AI assistant about your loan requirement. Share basic details like name and phone.</p>
            </div>
            
            <div className="text-center">
              <div className="w-20 h-20 bg-[#3B82F6] text-white rounded-full flex items-center justify-center mx-auto mb-4 text-3xl font-bold">
                2
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">Instant Verification</h3>
              <p className="text-base text-gray-600 leading-relaxed">AI verifies your profile, credit score, and eligibility in seconds using secure APIs.</p>
            </div>
            
            <div className="text-center">
              <div className="w-20 h-20 bg-[#3B82F6] text-white rounded-full flex items-center justify-center mx-auto mb-4 text-3xl font-bold">
                3
              </div>
              <h3 className="text-2xl font-semibold mb-3 text-gray-900">Get Approved</h3>
              <p className="text-base text-gray-600 leading-relaxed">Receive your sanction letter instantly and get funds disbursed to your account.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-6 bg-[#004589] text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-5xl font-bold mb-2">10M+</div>
              <div className="text-lg text-blue-200">Happy Customers</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">₹1L Cr+</div>
              <div className="text-lg text-blue-200">Loans Disbursed</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">600+</div>
              <div className="text-lg text-blue-200">Branches Across India</div>
            </div>
            <div>
              <div className="text-5xl font-bold mb-2">4.7★</div>
              <div className="text-lg text-blue-200">Customer Rating</div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-16 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">What Our Customers Say</h2>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { name: 'Priya S.', role: 'Software Engineer', text: 'Got my loan approved in 5 minutes! The AI assistant made it so easy.' },
              { name: 'Amit P.', role: 'Business Owner', text: 'Completely paperless process. Very convenient and transparent.' },
              { name: 'Dr. Aditi', role: 'Medical Professional', text: 'Excellent service. The interest rate was better than other banks.' }
            ].map((testimonial, index) => (
              <div key={index} className="bg-gray-50 p-6 rounded-xl">
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-amber-400">★</span>
                  ))}
                </div>
                <p className="text-gray-700 mb-4">&quot;{testimonial.text}&quot;</p>
                <div>
                  <div className="text-gray-900">{testimonial.name}</div>
                  <div className="text-sm text-gray-500">{testimonial.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Why Trust Tata Capital?</h2>
          </div>
          
          <div className="grid md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-[#004589]" />
              </div>
              <h4 className="mb-2 text-gray-900">RBI Licensed</h4>
              <p className="text-sm text-gray-600">Registered NBFC under Reserve Bank of India</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Award className="w-8 h-8 text-[#004589]" />
              </div>
              <h4 className="mb-2 text-gray-900">Award Winning</h4>
              <p className="text-sm text-gray-600">Multiple industry awards and recognitions</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-[#004589]" />
              </div>
              <h4 className="mb-2 text-gray-900">10M+ Customers</h4>
              <p className="text-sm text-gray-600">Trusted by millions across India</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-[#004589]" />
              </div>
              <h4 className="mb-2 text-gray-900">Tata Legacy</h4>
              <p className="text-sm text-gray-600">Part of the trusted Tata Group since 1991</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-[#004589] to-[#3B82F6]">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-3xl mb-4">Ready to Get Your Loan?</h2>
          <p className="text-xl mb-8 opacity-90">Chat with our AI assistant now. Takes less than 5 minutes!</p>
          <button className="bg-white text-[#004589] px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
            Start Chat Now
          </button>
        </div>
      </section>

      {/* Footer */}
      <Footer />

      {/* Floating Chat Widget */}
      <ChatWidget />
    </div>
  );
}