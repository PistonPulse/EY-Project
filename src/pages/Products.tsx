import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget } from '../components/ChatWidget';
import { Briefcase, Home, Building2, Car, Landmark, CreditCard, Check } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';

export function Products() {
  const products = [
    {
      icon: Briefcase,
      title: 'Personal Loans',
      description: 'Quick and hassle-free personal loans for all your needs',
      image: 'https://images.unsplash.com/photo-1635646917531-0806b8abcadd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBwcm9mZXNzaW9uYWwlMjBzbWFydHBob25lJTIwaGFwcHl8ZW58MXx8fHwxNzY1MTc3NTY3fDA&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: ₹50,000 to ₹25 lakhs',
        'Interest rate: Starting from 10.5% p.a.',
        'Tenure: 12 to 60 months',
        '100% paperless process',
        'Instant approval in 5 minutes',
        'No collateral required'
      ],
      color: 'from-blue-500 to-blue-600'
    },
    {
      icon: Home,
      title: 'Home Loans',
      description: 'Make your dream of owning a home come true',
      image: 'https://images.unsplash.com/photo-1730130596425-197566414dc4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbmRpYW4lMjBmYW1pbHklMjBob21lfGVufDF8fHx8MTc2NTE3OTI4OXww&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: Up to ₹10 crores',
        'Interest rate: Starting from 8.5% p.a.',
        'Tenure: Up to 30 years',
        'Tax benefits under Section 80C & 24',
        'Balance transfer facility available',
        'Top-up loan options'
      ],
      color: 'from-green-500 to-green-600'
    },
    {
      icon: Building2,
      title: 'Business Loans',
      description: 'Fuel your business growth with flexible financing',
      image: 'https://images.unsplash.com/photo-1630344745991-fb948c5bf9d1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxidXNpbmVzcyUyMGdyb3d0aCUyMHN1Y2Nlc3N8ZW58MXx8fHwxNzY1MTIxMjk2fDA&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: ₹5 lakhs to ₹75 lakhs',
        'Interest rate: Starting from 11% p.a.',
        'Tenure: 12 to 84 months',
        'Minimal documentation',
        'Flexible repayment options',
        'No collateral for loans up to ₹10 lakhs'
      ],
      color: 'from-amber-500 to-amber-600'
    },
    {
      icon: Landmark,
      title: 'Loan Against Property',
      description: 'Unlock the value of your property for any need',
      image: 'https://images.unsplash.com/photo-1694702740570-0a31ee1525c7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjUwOTExNzN8MA&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: Up to ₹10 crores',
        'Interest rate: Starting from 9.5% p.a.',
        'Tenure: Up to 20 years',
        'High loan-to-value ratio',
        'Multi-purpose usage',
        'Residential & commercial properties accepted'
      ],
      color: 'from-purple-500 to-purple-600'
    },
    {
      icon: Car,
      title: 'Used Car Loans',
      description: 'Drive home your dream car with easy financing',
      image: 'https://images.unsplash.com/photo-1694702740570-0a31ee1525c7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjUwOTExNzN8MA&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: Up to 90% of car value',
        'Interest rate: Starting from 12% p.a.',
        'Tenure: 12 to 60 months',
        'Quick approval in 24 hours',
        'Cars up to 10 years old',
        'Flexible EMI options'
      ],
      color: 'from-red-500 to-red-600'
    },
    {
      icon: CreditCard,
      title: 'Consumer Durable Loans',
      description: 'Buy electronics and appliances on easy EMI',
      image: 'https://images.unsplash.com/photo-1764231467896-73f0ef4438aa?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmaW5hbmNpYWwlMjBjYWxjdWxhdG9yJTIwcGxhbm5pbmd8ZW58MXx8fHwxNzY1MTc5MjkwfDA&ixlib=rb-4.1.0&q=80&w=1080',
      features: [
        'Loan amount: ₹5,000 to ₹2 lakhs',
        'Interest rate: Starting from 13% p.a.',
        'Tenure: 3 to 24 months',
        'Zero down payment options',
        'Instant in-store approval',
        'Wide range of partner stores'
      ],
      color: 'from-indigo-500 to-indigo-600'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6 bg-gradient-to-br from-[#004589] to-[#0066cc] text-white">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl mb-6">Our Products</h1>
          <p className="text-xl opacity-90 max-w-2xl mx-auto">
            Comprehensive financial solutions tailored to meet all your personal and business needs
          </p>
        </div>
      </section>

      {/* Products Grid */}
      <section className="py-16 px-6">
        <div className="max-w-7xl mx-auto space-y-16">
          {products.map((product, index) => {
            const Icon = product.icon;
            const isEven = index % 2 === 0;

            return (
              <div
                key={index}
                className={`grid lg:grid-cols-2 gap-8 items-center ${
                  isEven ? '' : 'lg:flex-row-reverse'
                }`}
              >
                {/* Image */}
                <div className={isEven ? 'lg:order-1' : 'lg:order-2'}>
                  <div className="relative">
                    <ImageWithFallback
                      src={product.image}
                      alt={product.title}
                      className="w-full h-80 object-cover rounded-xl shadow-xl"
                    />
                    <div className={`absolute top-6 left-6 w-16 h-16 bg-gradient-to-br ${product.color} rounded-xl flex items-center justify-center shadow-lg`}>
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className={isEven ? 'lg:order-2' : 'lg:order-1'}>
                  <div className="bg-white rounded-xl shadow-lg p-8">
                    <h2 className="text-3xl text-gray-900 mb-3">{product.title}</h2>
                    <p className="text-lg text-gray-600 mb-6">{product.description}</p>

                    <div className="space-y-3 mb-8">
                      {product.features.map((feature, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <div className={`w-6 h-6 bg-gradient-to-br ${product.color} rounded-full flex items-center justify-center flex-shrink-0 mt-0.5`}>
                            <Check className="w-4 h-4 text-white" />
                          </div>
                          <span className="text-gray-700">{feature}</span>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-4">
                      <button className={`flex-1 bg-gradient-to-r ${product.color} text-white py-3 rounded-lg hover:opacity-90 transition-opacity`}>
                        Apply Now
                      </button>
                      <button className="flex-1 border-2 border-[#004589] text-[#004589] py-3 rounded-lg hover:bg-[#004589] hover:text-white transition-colors">
                        Learn More
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Eligibility Section */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">General Eligibility Criteria</h2>
            <p className="text-xl text-gray-600">Basic requirements to apply for our loans</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl text-gray-900 mb-4">Age</h3>
              <p className="text-gray-600">21 to 65 years for salaried individuals, up to 70 years for self-employed</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl text-gray-900 mb-4">Income</h3>
              <p className="text-gray-600">Minimum monthly income of ₹15,000 for personal loans (varies by product)</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-6">
              <h3 className="text-xl text-gray-900 mb-4">Credit Score</h3>
              <p className="text-gray-600">CIBIL score of 650 or above (higher scores get better rates)</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-[#004589] to-[#3B82F6] text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Not Sure Which Product is Right for You?</h2>
          <p className="text-xl mb-8 opacity-90">
            Chat with our AI assistant to find the perfect loan product for your needs
          </p>
          <button className="bg-white text-[#004589] px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
            Talk to AI Assistant
          </button>
        </div>
      </section>

      <Footer />
      <ChatWidget />
    </div>
  );
}