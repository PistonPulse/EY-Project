import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { AIChatBanner } from '../components/AIChatBanner';
import { ChatWidget } from '../components/ChatWidget';
import { Award, Users, TrendingUp, Shield, Target, Heart, Lightbulb, Handshake } from 'lucide-react';
import { ImageWithFallback } from '../components/figma/ImageWithFallback';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";

export function About() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <AIChatBanner />

      {/* Hero Section */}
      <section className="pt-20 sm:pt-24 pb-12 sm:pb-16 px-4 sm:px-6 bg-gradient-to-br from-[#004589] to-[#0066cc] text-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-8 sm:gap-12 items-center">
            <div>
              <div className="bg-white rounded-lg p-2 sm:p-3 inline-block mb-4 sm:mb-6">
                <img src={tataLogo} alt="Tata Capital" className="h-10 sm:h-12 object-contain" />
              </div>
              <h1 className="text-3xl sm:text-4xl md:text-5xl mb-4 sm:mb-6">About Tata Capital</h1>
              <p className="text-lg sm:text-xl opacity-90 mb-4 sm:mb-6">
                A part of the Tata Group, Tata Capital is a leading financial services company
                offering comprehensive and innovative financial solutions to corporate and retail
                customers.
              </p>
              <div className="inline-block bg-yellow-400 text-[#004589] px-3 sm:px-4 py-1.5 sm:py-2 text-sm sm:text-base font-semibold">
                Part of the Tata Group since 1991
              </div>
            </div>
            <div>
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1531545514256-b1400bc00f31?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0ZWFtJTIwY29sbGFib3JhdGlvbiUyMG1lZXRpbmd8ZW58MXx8fHwxNzY1MTE1MjIxfDA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Team collaboration"
                className="w-full h-96 object-cover rounded-xl shadow-2xl"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#004589] rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-white" />
              </div>
              <div className="text-4xl text-[#004589] mb-2">10M+</div>
              <div className="text-gray-600">Happy Customers</div>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#004589] rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-white" />
              </div>
              <div className="text-4xl text-[#004589] mb-2">₹1L Cr+</div>
              <div className="text-gray-600">Loans Disbursed</div>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#004589] rounded-full flex items-center justify-center mx-auto mb-4">
                <Award className="w-8 h-8 text-white" />
              </div>
              <div className="text-4xl text-[#004589] mb-2">600+</div>
              <div className="text-gray-600">Branches</div>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#004589] rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <div className="text-4xl text-[#004589] mb-2">30+</div>
              <div className="text-gray-600">Years of Trust</div>
            </div>
          </div>
        </div>
      </section>

      {/* Mission & Vision */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12">
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-8 border border-blue-100">
              <div className="w-12 h-12 bg-[#004589] rounded-lg flex items-center justify-center mb-4">
                <Target className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-2xl text-gray-900 mb-4">Our Mission</h2>
              <p className="text-gray-700 leading-relaxed">
                To be the most trusted financial services provider in India, delivering innovative
                solutions that empower individuals and businesses to achieve their financial goals.
                We strive to combine the Tata Group's legacy of trust with cutting-edge technology
                and customer-first approach.
              </p>
            </div>

            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-8 border border-amber-100">
              <div className="w-12 h-12 bg-[#004589] rounded-lg flex items-center justify-center mb-4">
                <Lightbulb className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-2xl text-gray-900 mb-4">Our Vision</h2>
              <p className="text-gray-700 leading-relaxed">
                To create a financially inclusive India where every individual and business has
                access to seamless, transparent, and affordable financial services. We envision a
                future where technology and human touch work together to simplify financial
                decisions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Core Values */}
      <section className="py-16 px-6 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Our Core Values</h2>
            <p className="text-xl text-gray-600">The principles that guide everything we do</p>
          </div>

          <div className="grid md:grid-cols-4 gap-8">
            <div className="bg-white rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-[#004589]" />
              </div>
              <h3 className="text-xl text-gray-900 mb-2">Integrity</h3>
              <p className="text-gray-600">
                We uphold the highest standards of honesty and transparency in all our dealings
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Heart className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-2">Customer First</h3>
              <p className="text-gray-600">
                Our customers are at the heart of everything we do
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Lightbulb className="w-8 h-8 text-amber-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-2">Innovation</h3>
              <p className="text-gray-600">
                We continuously innovate to deliver better solutions
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Handshake className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl text-gray-900 mb-2">Trust</h3>
              <p className="text-gray-600">
                We build lasting relationships based on trust and reliability
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tata Group Legacy */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1694702740570-0a31ee1525c7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjBidWlsZGluZ3xlbnwxfHx8fDE3NjUwOTExNzN8MA&ixlib=rb-4.1.0&q=80&w=1080"
                alt="Tata Group Legacy"
                className="w-full h-96 object-cover rounded-xl shadow-xl"
              />
            </div>
            <div>
              <h2 className="text-3xl text-gray-900 mb-6">The Tata Group Legacy</h2>
              <p className="text-gray-700 mb-4 leading-relaxed">
                Founded in 1868, the Tata Group is one of India's largest and most respected
                business conglomerates. With operations in over 100 countries across six continents,
                Tata companies employ over 935,000 people.
              </p>
              <p className="text-gray-700 mb-6 leading-relaxed">
                Tata Capital, established in 2007, carries forward this rich legacy of trust,
                innovation, and nation-building. We bring the same values of integrity,
                responsibility, and excellence that have made the Tata name synonymous with trust
                across India.
              </p>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-[#004589] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Award className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="text-gray-900 mb-1">Heritage of Excellence</div>
                    <div className="text-sm text-gray-600">
                      150+ years of the Tata Group's trusted legacy
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-[#004589] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Shield className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="text-gray-900 mb-1">RBI Regulated</div>
                    <div className="text-sm text-gray-600">
                      Registered NBFC under Reserve Bank of India
                    </div>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 bg-[#004589] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Users className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <div className="text-gray-900 mb-1">Customer Trust</div>
                    <div className="text-sm text-gray-600">
                      10 million+ satisfied customers across India
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Awards & Recognition */}
      <section className="py-16 px-6 bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl text-gray-900 mb-4">Awards & Recognition</h2>
            <p className="text-xl text-gray-600">
              Recognized for excellence in financial services
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                award: 'Best NBFC - Consumer Finance',
                year: '2024',
                organization: 'Financial Express'
              },
              {
                award: 'Excellence in Digital Innovation',
                year: '2023',
                organization: 'BFSI Awards'
              },
              {
                award: 'Best Customer Service Award',
                year: '2023',
                organization: 'India Business Awards'
              },
              {
                award: 'Top Employer Award',
                year: '2024',
                organization: 'Top Employers Institute'
              },
              {
                award: 'Excellence in Financial Inclusion',
                year: '2023',
                organization: 'Banking Frontier Awards'
              },
              {
                award: 'Best Financial Services Brand',
                year: '2024',
                organization: 'Brand Equity'
              }
            ].map((item, index) => (
              <div
                key={index}
                className="bg-white rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow"
              >
                <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-amber-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Award className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-lg text-gray-900 mb-2">{item.award}</h3>
                <p className="text-gray-600 text-sm mb-1">{item.organization}</p>
                <p className="text-[#004589]">{item.year}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 bg-gradient-to-r from-[#004589] to-[#3B82F6] text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl mb-4">Join Millions Who Trust Tata Capital</h2>
          <p className="text-xl mb-8 opacity-90">
            Experience the perfect blend of legacy, innovation, and customer service
          </p>
          <button className="bg-white text-[#004589] px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors">
            Get Started Today
          </button>
        </div>
      </section>

      <Footer />
      <ChatWidget />
    </div>
  );
}